ENTRY(Reset_Handler)

MEMORY
{
    SLOTA (rx) : ORIGIN = 0x10002000, LENGTH = 0x37000
    SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 0x20000
}

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > SLOTA

    .text :
    {
        *(.text*)
        *(.rodata*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame*)
    } > SLOTA

    .data :
    {
        *(.data*)
    } > SRAM AT > SLOTA

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
    } > SRAM

    __stack_top = ORIGIN(SRAM) + LENGTH(SRAM);
}
