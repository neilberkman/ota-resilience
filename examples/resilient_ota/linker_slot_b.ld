ENTRY(Reset_Handler)

MEMORY
{
    SLOTB (rx) : ORIGIN = 0x10039000, LENGTH = 0x37000
    SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 0x20000
}

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > SLOTB

    .text :
    {
        *(.text*)
        *(.rodata*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame*)
    } > SLOTB

    .data :
    {
        *(.data*)
    } > SRAM AT > SLOTB

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
    } > SRAM

    __stack_top = ORIGIN(SRAM) + LENGTH(SRAM);
}
