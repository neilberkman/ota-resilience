#include <stdint.h>

#ifndef SLOT_ID
#define SLOT_ID 0
#endif

#define BOOT_SLOT_MARKER_ADDR ((uintptr_t)0x10070220u)
#define BOOT_TICKS_ADDR       ((uintptr_t)0x10070224u)

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

void Reset_Handler(void)
{
    *(volatile uint32_t*)BOOT_SLOT_MARKER_ADDR = (uint32_t)SLOT_ID;
    *(volatile uint32_t*)BOOT_TICKS_ADDR = *(volatile uint32_t*)BOOT_TICKS_ADDR + 1u;

    while(1)
    {
    }
}
