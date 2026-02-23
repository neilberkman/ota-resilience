/*
 * Bootloader with compile-time selectable defects for self-testing.
 *
 * Build with -DDEFECT=<name> to inject a specific known bug class:
 *
 *   DEFECT_NONE               - correct resilient bootloader (baseline)
 *   DEFECT_NO_FALLBACK        - skip fallback to alternate slot on invalid vectors
 *   DEFECT_NO_VECTOR_CHECK    - jump to slot without validating vectors
 *   DEFECT_BOTH_REPLICAS_RACE - write both metadata replicas atomically (single-point-of-failure)
 *   DEFECT_CRC_OFF_BY_ONE     - CRC covers one fewer byte (silent metadata corruption)
 *   DEFECT_SEQ_NAIVE          - use plain < instead of wrapping comparison for seq numbers
 *   DEFECT_NO_BOOT_COUNT      - never increment boot_count (trial boot can't expire)
 *
 * These mirror real-world bug classes found in MCUboot and other bootloaders.
 * The audit tool should detect each defect's failure mode.
 */

#include <stdint.h>

/* Include the same boot_meta.h but we may override individual functions. */
#include "boot_meta.h"

#define SLOT_A_BASE       ((uintptr_t)0x10002000u)
#define SLOT_B_BASE       ((uintptr_t)0x10039000u)
#define SLOT_SIZE         (0x37000u)
#define META_BASE         ((uintptr_t)0x10070000u)
#define PERSIST_BOOT_ADDR ((uintptr_t)0x10070200u)
#define SCB_VTOR_ADDR     ((uintptr_t)0xE000ED08u)
#define SRAM_START        ((uintptr_t)0x20000000u)
#define SRAM_END          ((uintptr_t)0x20020000u)

#ifndef ENABLE_VTOR_RELOCATION
#define ENABLE_VTOR_RELOCATION 1
#endif

/* --- Defect selection --- */
#ifndef DEFECT
#define DEFECT DEFECT_NONE
#endif

#define DEFECT_NONE               0
#define DEFECT_NO_FALLBACK        1
#define DEFECT_NO_VECTOR_CHECK    2
#define DEFECT_BOTH_REPLICAS_RACE 3
#define DEFECT_CRC_OFF_BY_ONE     4
#define DEFECT_SEQ_NAIVE          5
#define DEFECT_NO_BOOT_COUNT      6

extern uint32_t __stack_top;

void Reset_Handler(void);
void Default_Handler(void);

__attribute__((section(".isr_vector")))
const void* vector_table[] = {
    &__stack_top,
    Reset_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    Default_Handler,
    0,
    0,
    0,
    0,
    Default_Handler,
    Default_Handler,
    0,
    Default_Handler,
    Default_Handler,
};

void Default_Handler(void)
{
    while(1)
    {
    }
}

static uintptr_t slot_base_for_id(uint32_t id)
{
    return (id == SLOT_B) ? SLOT_B_BASE : SLOT_A_BASE;
}

/* --- CRC override for DEFECT_CRC_OFF_BY_ONE --- */
#if (DEFECT == DEFECT_CRC_OFF_BY_ONE)
/*
 * Bug: CRC covers payload_size - 1 bytes instead of payload_size.
 * This means the last byte before the CRC field is unprotected.
 * A single-bit flip there won't be detected, allowing silent metadata corruption.
 */
static uint32_t variant_meta_crc(const boot_meta_t* meta)
{
    const uint8_t* bytes = (const uint8_t*)meta;
    uint32_t crc = 0xFFFFFFFFu;
    /* BUG: should be BOOT_META_REPLICA_SIZE - sizeof(uint32_t), but we subtract 1 more */
    const uint32_t payload_size = BOOT_META_REPLICA_SIZE - sizeof(uint32_t) - 1u;

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
#endif

/* --- Sequence comparison override for DEFECT_SEQ_NAIVE --- */
#if (DEFECT == DEFECT_SEQ_NAIVE)
/*
 * Bug: plain >= comparison instead of wrapping modular arithmetic.
 * Breaks when sequence numbers wrap around 0xFFFFFFFF -> 0x00000000.
 * A freshly-wrapped seq=1 would lose to a stale seq=0xFFFFFFFF.
 */
static int variant_seq_ge(uint32_t lhs, uint32_t rhs)
{
    return (lhs >= rhs) ? 1 : 0;
}
#endif

/* --- Meta select that uses our variant overrides --- */
static const boot_meta_t* variant_meta_select(uintptr_t meta_base)
{
    const boot_meta_t* r0 = (const boot_meta_t*)meta_base;
    const boot_meta_t* r1 = (const boot_meta_t*)(meta_base + BOOT_META_REPLICA_SIZE);

#if (DEFECT == DEFECT_CRC_OFF_BY_ONE)
    const int valid0 = (r0->magic == BOOT_META_MAGIC) && (r0->crc == variant_meta_crc(r0));
    const int valid1 = (r1->magic == BOOT_META_MAGIC) && (r1->crc == variant_meta_crc(r1));
#else
    const int valid0 = (r0->magic == BOOT_META_MAGIC) && (r0->crc == boot_meta_crc(r0));
    const int valid1 = (r1->magic == BOOT_META_MAGIC) && (r1->crc == boot_meta_crc(r1));
#endif

    if(valid0 && valid1)
    {
#if (DEFECT == DEFECT_SEQ_NAIVE)
        return variant_seq_ge(r0->seq, r1->seq) ? r0 : r1;
#else
        return boot_meta_seq_ge(r0->seq, r1->seq) ? r0 : r1;
#endif
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

static void repair_meta_to_confirmed_slot(const boot_meta_t* meta, uint32_t slot)
{
    boot_meta_t updated;

    boot_meta_clear(&updated);
    if(meta != 0)
    {
        boot_meta_copy(&updated, meta);
        updated.seq = meta->seq + 1u;
        updated.max_boot_count = boot_meta_effective_max(meta);
    }
    else
    {
        updated.seq = 1u;
        updated.max_boot_count = BOOT_META_MAX_BOOT_COUNT;
    }

    updated.active_slot = slot;
    updated.target_slot = slot;
    updated.state = BOOT_STATE_CONFIRMED;
    updated.boot_count = 0u;

#if (DEFECT == DEFECT_BOTH_REPLICAS_RACE)
    /*
     * Bug: write both replicas with identical content and no ordering guarantee.
     * A power loss during this window corrupts BOTH replicas simultaneously.
     * Correct behavior: write stale replica first, barrier, then fresh replica.
     */
    {
        volatile uint32_t* replica0 = (volatile uint32_t*)META_BASE;
        volatile uint32_t* replica1 = (volatile uint32_t*)(META_BASE + BOOT_META_REPLICA_SIZE);
        const uint32_t* words;

        updated.magic = BOOT_META_MAGIC;
        if(updated.max_boot_count == 0u)
        {
            updated.max_boot_count = BOOT_META_MAX_BOOT_COUNT;
        }
        updated.crc = 0u;
        updated.crc = boot_meta_crc(&updated);

        words = (const uint32_t*)&updated;
        /* BUG: interleaved writes to both replicas */
        for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
        {
            replica0[i] = words[i];
            replica1[i] = words[i];
        }
    }
#else
    boot_meta_write_replicas(META_BASE, &updated);
#endif
}

static int slot_vector_is_valid(uintptr_t slot_base)
{
#if (DEFECT == DEFECT_NO_VECTOR_CHECK)
    /*
     * Bug: always reports vectors as valid. The bootloader will jump to
     * whatever is at the slot base even if it's garbage, partial write,
     * or erased NVM (all 0xFF). Results in hard fault or execution of
     * random memory.
     */
    (void)slot_base;
    return 1;
#else
    const uint32_t initial_sp = *(const uint32_t*)(slot_base + 0u);
    const uint32_t reset_vector = *(const uint32_t*)(slot_base + 4u);
    const uintptr_t reset_pc = (uintptr_t)(reset_vector & (~1u));

    if(initial_sp < SRAM_START || initial_sp > SRAM_END)
    {
        return 0;
    }

    if(reset_pc < slot_base || reset_pc >= (slot_base + SLOT_SIZE))
    {
        return 0;
    }

    if((reset_vector & 1u) == 0)
    {
        return 0;
    }

    return 1;
#endif
}

static void jump_to_slot(uintptr_t slot_base)
{
    const uint32_t initial_sp = *(const uint32_t*)(slot_base + 0u);
    const uint32_t reset_vector = *(const uint32_t*)(slot_base + 4u);
    void (*entry)(void) = (void (*)(void))reset_vector;

#if ENABLE_VTOR_RELOCATION
    *(volatile uint32_t*)SCB_VTOR_ADDR = (uint32_t)slot_base;
#endif
    __asm volatile("dsb" ::: "memory");
    __asm volatile("isb" ::: "memory");
    __asm volatile("msr msp, %0" : : "r"(initial_sp) : "memory");
    __asm volatile("dsb" ::: "memory");
    __asm volatile("isb" ::: "memory");
    entry();
}

void Reset_Handler(void)
{
    const boot_meta_t* meta = variant_meta_select(META_BASE);
    uint32_t active_slot = SLOT_A;
    uintptr_t chosen_base;

    if(meta != 0)
    {
        active_slot = meta->active_slot;

        if(meta->state == BOOT_STATE_PENDING_TEST)
        {
            const uint32_t max_count = boot_meta_effective_max(meta);

            if(meta->boot_count >= max_count)
            {
                boot_meta_t updated;
                const uint32_t reverted_slot = (active_slot == SLOT_A) ? SLOT_B : SLOT_A;

                boot_meta_copy(&updated, meta);
                updated.seq = meta->seq + 1u;
                updated.active_slot = reverted_slot;
                updated.target_slot = reverted_slot;
                updated.state = BOOT_STATE_CONFIRMED;
                updated.boot_count = 0u;
                updated.max_boot_count = max_count;

#if (DEFECT == DEFECT_BOTH_REPLICAS_RACE)
                {
                    volatile uint32_t* replica0 = (volatile uint32_t*)META_BASE;
                    volatile uint32_t* replica1 = (volatile uint32_t*)(META_BASE + BOOT_META_REPLICA_SIZE);
                    const uint32_t* words;

                    updated.magic = BOOT_META_MAGIC;
                    updated.crc = 0u;
                    updated.crc = boot_meta_crc(&updated);

                    words = (const uint32_t*)&updated;
                    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
                    {
                        replica0[i] = words[i];
                        replica1[i] = words[i];
                    }
                }
#else
                boot_meta_write_replicas(META_BASE, &updated);
#endif

                active_slot = reverted_slot;
            }
            else
            {
#if (DEFECT == DEFECT_NO_BOOT_COUNT)
                /*
                 * Bug: never increments boot_count. Trial boot can never expire,
                 * so a failing firmware will keep rebooting forever without ever
                 * reverting to the known-good slot.
                 */
                (void)max_count;
#else
                boot_meta_t updated;

                boot_meta_copy(&updated, meta);
                updated.seq = meta->seq + 1u;
                updated.boot_count = meta->boot_count + 1u;
                updated.max_boot_count = max_count;

#if (DEFECT == DEFECT_BOTH_REPLICAS_RACE)
                {
                    volatile uint32_t* replica0 = (volatile uint32_t*)META_BASE;
                    volatile uint32_t* replica1 = (volatile uint32_t*)(META_BASE + BOOT_META_REPLICA_SIZE);
                    const uint32_t* words;

                    updated.magic = BOOT_META_MAGIC;
                    updated.crc = 0u;
                    updated.crc = boot_meta_crc(&updated);

                    words = (const uint32_t*)&updated;
                    for(uint32_t i = 0u; i < (BOOT_META_REPLICA_SIZE / 4u); i++)
                    {
                        replica0[i] = words[i];
                        replica1[i] = words[i];
                    }
                }
#else
                boot_meta_write_replicas(META_BASE, &updated);
#endif
#endif
            }
        }
    }

    chosen_base = slot_base_for_id(active_slot);

    if(!slot_vector_is_valid(chosen_base))
    {
#if (DEFECT == DEFECT_NO_FALLBACK)
        /*
         * Bug: no fallback logic. If the active slot has invalid vectors,
         * the bootloader just tries to boot it anyway (or hangs). In real
         * systems this means a corrupted OTA image = permanent brick.
         */
        /* Fall through to jump attempt below with invalid vectors. */
#else
        const uint32_t fallback_slot = (active_slot == SLOT_A) ? SLOT_B : SLOT_A;
        const uintptr_t fallback_base = slot_base_for_id(fallback_slot);

        if(slot_vector_is_valid(fallback_base))
        {
            active_slot = fallback_slot;
            chosen_base = fallback_base;
            repair_meta_to_confirmed_slot(variant_meta_select(META_BASE), fallback_slot);
        }
#endif
    }

    *(volatile uint32_t*)PERSIST_BOOT_ADDR = active_slot;

    if(slot_vector_is_valid(chosen_base))
    {
        jump_to_slot(chosen_base);
    }

    while(1)
    {
    }
}
