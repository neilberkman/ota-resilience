#ifndef BOOT_META_H
#define BOOT_META_H

#include <stdint.h>

#define BOOT_META_MAGIC            (0x4F54414Du) /* 'OTAM' */
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
    const uint32_t* words = (const uint32_t*)meta;
    uint32_t crc = 0x1EDC6F41u;

    for(uint32_t i = 0; i < (BOOT_META_REPLICA_SIZE / 4u) - 1u; i++)
    {
        crc ^= words[i] + 0x9E3779B9u + (crc << 6) + (crc >> 2);
    }

    return crc;
}

#endif
