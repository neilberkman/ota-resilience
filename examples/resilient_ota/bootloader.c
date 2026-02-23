#include <stdint.h>

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
/*
 * Default to VTOR relocation enabled because this demo targets Cortex-M0+.
 * Cortex-M0 builds must disable it via build flags.
 */
#define ENABLE_VTOR_RELOCATION 1
#endif

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

    boot_meta_write_replicas(META_BASE, &updated);
}

static int slot_vector_is_valid(uintptr_t slot_base)
{
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
    const boot_meta_t* meta = boot_meta_select(META_BASE);
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
                boot_meta_write_replicas(META_BASE, &updated);

                active_slot = reverted_slot;
            }
            else
            {
                boot_meta_t updated;

                boot_meta_copy(&updated, meta);
                updated.seq = meta->seq + 1u;
                updated.boot_count = meta->boot_count + 1u;
                updated.max_boot_count = max_count;
                boot_meta_write_replicas(META_BASE, &updated);
            }
        }
    }

    chosen_base = slot_base_for_id(active_slot);

    if(!slot_vector_is_valid(chosen_base))
    {
        const uint32_t fallback_slot = (active_slot == SLOT_A) ? SLOT_B : SLOT_A;
        const uintptr_t fallback_base = slot_base_for_id(fallback_slot);

        if(slot_vector_is_valid(fallback_base))
        {
            active_slot = fallback_slot;
            chosen_base = fallback_base;
            repair_meta_to_confirmed_slot(boot_meta_select(META_BASE), fallback_slot);
        }
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
