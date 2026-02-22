*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                 ${CURDIR}/..
${PLATFORM}             ${ROOT}/platforms/cortex_m0_nvm.repl
${FLASH_PLATFORM}       ${ROOT}/platforms/cortex_m4_flash.repl
${PERIPHERAL_CS}        ${ROOT}/peripherals/NVMemoryController.cs

*** Keywords ***
Create NVM Machine
    Execute Command    include "${PERIPHERAL_CS}"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM}

Create Flash NVM Machine
    Execute Command    include "${PERIPHERAL_CS}"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${FLASH_PLATFORM}

*** Test Cases ***
NVM Persists Across Reset
    Create NVM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000040 0x11223344
    Execute Command    machine Reset
    ${after}=          Execute Command    sysbus ReadDoubleWord 0x10000040
    Should Be Equal As Numbers    ${after}    0x11223344

Word-Write Erase-Then-Program Semantics
    Create NVM Machine
    Execute Command    sysbus WriteQuadWord 0x10000080 0x1122334455667788
    Execute Command    sysbus WriteDoubleWord 0x10000084 0xAABBCCDD
    ${merged}=         Execute Command    sysbus ReadQuadWord 0x10000080
    Should Be Equal As Numbers    ${merged}    0xAABBCCDD55667788

Partial Write Corruption
    Create NVM Machine
    Execute Command    sysbus WriteQuadWord 0x10000100 0x0123456789ABCDEF
    Execute Command    sysbus.nvm_ctrl InjectPartialWrite 0x10000100
    ${faulted}=        Execute Command    sysbus ReadQuadWord 0x10000100
    Should Not Be Equal As Numbers    ${faulted}    0x0123456789ABCDEF

NV Read Alias Returns Same Data
    Create NVM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000180 0xDEADBEEF
    ${main}=           Execute Command    sysbus ReadDoubleWord 0x10000180
    ${alias}=          Execute Command    sysbus ReadDoubleWord 0x10080180
    Should Be Equal As Numbers    ${main}    0xDEADBEEF
    Should Be Equal As Numbers    ${alias}    0xDEADBEEF

NV Read Alias Drops Writes
    Create NVM Machine
    Execute Command    sysbus WriteDoubleWord 0x100001C0 0xCAFEBABE
    Execute Command    sysbus WriteDoubleWord 0x100801C0 0x11223344
    ${main_after}=     Execute Command    sysbus ReadDoubleWord 0x100001C0
    ${alias_after}=    Execute Command    sysbus ReadDoubleWord 0x100801C0
    Should Be Equal As Numbers    ${main_after}    0xCAFEBABE
    Should Be Equal As Numbers    ${alias_after}    0xCAFEBABE

NV Read Alias Drops Sequential Writes
    Create NVM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000200 0xAAAAAAAA
    Execute Command    sysbus WriteDoubleWord 0x10000204 0xBBBBBBBB
    Execute Command    sysbus WriteDoubleWord 0x10080200 0x11111111
    Execute Command    sysbus WriteDoubleWord 0x10080204 0x22222222
    ${main0}=          Execute Command    sysbus ReadDoubleWord 0x10000200
    ${main1}=          Execute Command    sysbus ReadDoubleWord 0x10000204
    ${alias0}=         Execute Command    sysbus ReadDoubleWord 0x10080200
    ${alias1}=         Execute Command    sysbus ReadDoubleWord 0x10080204
    Should Be Equal As Numbers    ${main0}    0xAAAAAAAA
    Should Be Equal As Numbers    ${main1}    0xBBBBBBBB
    Should Be Equal As Numbers    ${alias0}    0xAAAAAAAA
    Should Be Equal As Numbers    ${alias1}    0xBBBBBBBB

Flash Sector Erase
    Create Flash NVM Machine
    Execute Command    sysbus.nvm_ctrl EraseSector 0x00001044
    ${start}=          Execute Command    sysbus ReadByte 0x00001000
    ${end}=            Execute Command    sysbus ReadByte 0x00001FFF
    Should Be Equal As Numbers    ${start}    0xFF
    Should Be Equal As Numbers    ${end}    0xFF

Flash Page Write
    Create Flash NVM Machine
    Execute Command    sysbus.nvm_ctrl EraseSector 0x00002000
    Execute Command    sysbus WriteQuadWord 0x00002000 0x0123456789ABCDEF
    Execute Command    sysbus WriteQuadWord 0x000020F8 0xFFEEDDCCBBAA9988
    ${head}=           Execute Command    sysbus ReadQuadWord 0x00002000
    ${tail}=           Execute Command    sysbus ReadQuadWord 0x000020F8
    Should Be Equal As Numbers    ${head}    0x0123456789ABCDEF
    Should Be Equal As Numbers    ${tail}    0xFFEEDDCCBBAA9988

Flash Partial Page Write
    Create Flash NVM Machine
    Execute Command    sysbus.nvm_ctrl EraseSector 0x00003000
    Execute Command    sysbus.nvm_ctrl InjectPartialWrite 0x00003000
    ${first_half}=     Execute Command    sysbus ReadByte 0x00003000
    ${second_half}=    Execute Command    sysbus ReadByte 0x00003080
    Should Be Equal As Numbers    ${first_half}    0x00
    Should Be Equal As Numbers    ${second_half}    0xFF

Flash Partial Erase
    Create Flash NVM Machine
    Execute Command    sysbus.nvm_ctrl EraseSector 0x00004000
    Execute Command    sysbus WriteByte 0x00004000 0x00
    Execute Command    sysbus WriteByte 0x00004BB8 0x00
    Execute Command    sysbus.nvm_ctrl InjectPartialErase 0x00004000
    ${first_half}=     Execute Command    sysbus ReadByte 0x00004000
    ${second_half}=    Execute Command    sysbus ReadByte 0x00004BB8
    Should Be Equal As Numbers    ${first_half}    0xFF
    Should Be Equal As Numbers    ${second_half}    0x00

Erase-Before-Write Enforcement
    Create Flash NVM Machine
    Execute Command    sysbus WriteDoubleWord 0x00005000 0x11223344
    ${rejected}=       Execute Command    sysbus ReadDoubleWord 0x00005000
    Should Be Equal As Numbers    ${rejected}    0x00000000
    Execute Command    sysbus.nvm_ctrl EraseSector 0x00005000
    Execute Command    sysbus WriteDoubleWord 0x00005000 0x11223344
    ${programmed}=     Execute Command    sysbus ReadDoubleWord 0x00005000
    Should Be Equal As Numbers    ${programmed}    0x11223344
