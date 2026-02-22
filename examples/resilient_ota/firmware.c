#include <stdint.h>

#include "boot_meta.h"

#ifndef SLOT_ID
#define SLOT_ID 0
#endif

#define BOOT_SLOT_MARKER_ADDR ((uintptr_t)0x10070220u)
#define BOOT_TICKS_ADDR       ((uintptr_t)0x10070224u)
#define META_BASE             ((uintptr_t)0x10070000u)

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

static void confirm_boot(void)
{
    const boot_meta_t* active = boot_meta_select(META_BASE);
    boot_meta_t updated;

    boot_meta_clear(&updated);

    if(active != 0)
    {
        boot_meta_copy(&updated, active);
        updated.seq = active->seq + 1u;
    }
    else
    {
        updated.seq = 1u;
        updated.max_boot_count = BOOT_META_MAX_BOOT_COUNT;
    }

    updated.active_slot = (uint32_t)SLOT_ID;
    updated.target_slot = (uint32_t)SLOT_ID;
    updated.state = BOOT_STATE_CONFIRMED;
    updated.boot_count = 0u;

    boot_meta_write_replicas(META_BASE, &updated);
}

void Reset_Handler(void)
{
    *(volatile uint32_t*)BOOT_SLOT_MARKER_ADDR = (uint32_t)SLOT_ID;
    *(volatile uint32_t*)BOOT_TICKS_ADDR = *(volatile uint32_t*)BOOT_TICKS_ADDR + 1u;
    confirm_boot();

    while(1)
    {
    }
}
