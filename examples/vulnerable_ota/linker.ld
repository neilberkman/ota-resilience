ENTRY(Reset_Handler)

MEMORY
{
    NVM (rx)   : ORIGIN = 0x10000000, LENGTH = 0x38000
    SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 0x20000
}

SECTIONS
{
    .isr_vector :
    {
        KEEP(*(.isr_vector))
    } > NVM

    .text :
    {
        *(.text*)
        *(.rodata*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame*)
    } > NVM

    .ramfunc :
    {
        _sramfunc = .;
        *(.ramfunc*)
        _eramfunc = .;
    } > SRAM AT > NVM
    _siramfunc = LOADADDR(.ramfunc);

    .data :
    {
        _sdata = .;
        *(.data*)
        _edata = .;
    } > SRAM AT > NVM
    _sidata = LOADADDR(.data);

    .bss (NOLOAD) :
    {
        _sbss = .;
        *(.bss*)
        *(COMMON)
        _ebss = .;
    } > SRAM

    __stack_top = ORIGIN(SRAM) + LENGTH(SRAM);
}
