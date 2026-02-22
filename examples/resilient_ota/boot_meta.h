#ifndef BOOT_META_H
#define BOOT_META_H

#include <stdint.h>

#define BOOT_META_MAGIC            (0x4F54414Du) /* numeric tag for ASCII "OTAM" */
#define BOOT_META_REPLICA_SIZE     (256u)
#define BOOT_META_MAX_BOOT_COUNT   (3u)

typedef enum
{
    SLOT_A = 0,
    SLOT_B = 1,
} slot_id_t;

typedef enum
{
    BOOT_STATE_CONFIRMED = 0,
    BOOT_STATE_PENDING_TEST = 1,
} boot_state_t;

typedef struct
{
    uint32_t magic;
    uint32_t seq;
    uint32_t active_slot;
    uint32_t target_slot;
    uint32_t state;
    uint32_t boot_count;
    uint32_t max_boot_count;
    uint32_t reserved0;
    uint32_t reserved[(BOOT_META_REPLICA_SIZE / 4u) - 9u];
    uint32_t crc;
} boot_meta_t;

static inline uint32_t boot_meta_crc(const boot_meta_t* meta)
{
    const uint8_t* bytes = (const uint8_t*)meta;
    uint32_t crc = 0xFFFFFFFFu;
    const uint32_t payload_size = BOOT_META_REPLICA_SIZE - sizeof(uint32_t);

    for(uint32_t i = 0u; i < payload_size; i++)
    {
        crc ^= bytes[i];
        for(uint32_t b = 0u; b < 8u; b++)
        {
            crc = (crc >> 1) ^ ((crc & 1u) ? 0xEDB88320u : 0u);
        }
    }

    return crc ^ 0xFFFFFFFFu;
}

static inline void boot_meta_copy(boot_meta_t* dst, const boot_meta_t* src)
{
    uint32_t* d = (uint32_t*)dst;
    const uint32_t* s = (const uint32_t*)src;

    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
    {
        d[i] = s[i];
    }
}

static inline void boot_meta_clear(boot_meta_t* dst)
{
    uint32_t* d = (uint32_t*)dst;

    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
    {
        d[i] = 0u;
    }
}

static inline int boot_meta_seq_ge(uint32_t lhs, uint32_t rhs)
{
    return ((int32_t)(lhs - rhs) >= 0) ? 1 : 0;
}

static inline const boot_meta_t* boot_meta_select(uintptr_t meta_base)
{
    const boot_meta_t* r0 = (const boot_meta_t*)meta_base;
    const boot_meta_t* r1 = (const boot_meta_t*)(meta_base + BOOT_META_REPLICA_SIZE);

    const int valid0 = (r0->magic == BOOT_META_MAGIC) && (r0->crc == boot_meta_crc(r0));
    const int valid1 = (r1->magic == BOOT_META_MAGIC) && (r1->crc == boot_meta_crc(r1));

    if(valid0 && valid1)
    {
        return boot_meta_seq_ge(r0->seq, r1->seq) ? r0 : r1;
    }

    if(valid0)
    {
        return r0;
    }

    if(valid1)
    {
        return r1;
    }

    return (const boot_meta_t*)0;
}

static inline uint32_t boot_meta_effective_max(const boot_meta_t* meta)
{
    return (meta->max_boot_count == 0u) ? BOOT_META_MAX_BOOT_COUNT : meta->max_boot_count;
}

static inline void boot_meta_write_replicas(uintptr_t meta_base, boot_meta_t* next)
{
    const uint32_t* words;
    const boot_meta_t* current0 = (const boot_meta_t*)meta_base;
    const boot_meta_t* current1 = (const boot_meta_t*)(meta_base + BOOT_META_REPLICA_SIZE);
    const int valid0 = (current0->magic == BOOT_META_MAGIC) && (current0->crc == boot_meta_crc(current0));
    const int valid1 = (current1->magic == BOOT_META_MAGIC) && (current1->crc == boot_meta_crc(current1));
    volatile uint32_t* replica0 = (volatile uint32_t*)meta_base;
    volatile uint32_t* replica1 = (volatile uint32_t*)(meta_base + BOOT_META_REPLICA_SIZE);
    volatile uint32_t* first = replica0;
    volatile uint32_t* second = replica1;

    next->magic = BOOT_META_MAGIC;
    if(next->max_boot_count == 0u)
    {
        next->max_boot_count = BOOT_META_MAX_BOOT_COUNT;
    }
    next->crc = 0u;
    next->crc = boot_meta_crc(next);

    if(valid0 && !valid1)
    {
        first = replica1;
        second = replica0;
    }
    else if(valid0 && valid1)
    {
        if(boot_meta_seq_ge(current0->seq, current1->seq))
        {
            first = replica1;
            second = replica0;
        }
        else
        {
            first = replica0;
            second = replica1;
        }
    }

    words = (const uint32_t*)next;
    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
    {
        first[i] = words[i];
    }

    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
    {
        second[i] = words[i];
    }
}

#endif
