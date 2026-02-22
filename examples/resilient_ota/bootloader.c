#include <stdint.h>

#include "boot_meta.h"

#define SLOT_A_BASE       ((uintptr_t)0x10002000u)
#define SLOT_B_BASE       ((uintptr_t)0x10039000u)
#define SLOT_SIZE         (0x37000u)
#define META_BASE         ((uintptr_t)0x10070000u)
#define PERSIST_BOOT_ADDR ((uintptr_t)0x10070200u)
#define SRAM_START        ((uintptr_t)0x20000000u)
#define SRAM_END          ((uintptr_t)0x20020000u)

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

static const boot_meta_t* select_metadata(void)
{
    const boot_meta_t* r0 = (const boot_meta_t*)META_BASE;
    const boot_meta_t* r1 = (const boot_meta_t*)(META_BASE + BOOT_META_REPLICA_SIZE);

    const int valid0 = (r0->magic == BOOT_META_MAGIC) && (r0->crc == boot_meta_crc(r0));
    const int valid1 = (r1->magic == BOOT_META_MAGIC) && (r1->crc == boot_meta_crc(r1));

    if(valid0 && valid1)
    {
        return (r0->seq >= r1->seq) ? r0 : r1;
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

static uintptr_t slot_base_for_id(uint32_t id)
{
    return (id == SLOT_B) ? SLOT_B_BASE : SLOT_A_BASE;
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

    __asm volatile("msr msp, %0" : : "r"(initial_sp) : );
    entry();
}

void Reset_Handler(void)
{
    const boot_meta_t* meta = select_metadata();
    uint32_t active_slot = SLOT_A;
    uintptr_t chosen_base;

    if(meta != 0)
    {
        active_slot = meta->active_slot;
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
