*** Keywords ***
Create MRAM Machine
    Execute Command    include "${CURDIR}/../peripherals/MRAMController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${CURDIR}/../platforms/cortex_m0_mram.repl

*** Test Cases ***
MRAM Persists Across Reset
    Create MRAM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000000 0xAABBCCDD
    Execute Command    mram Reset
    ${read_back}=      Execute Command    sysbus ReadDoubleWord 0x10000000
    Should Be Equal As Numbers    ${read_back}    0xAABBCCDD

MRAM Write Requires Erase First
    Create MRAM Machine
    Execute Command    sysbus WriteQuadWord 0x10000000 0xFFEEDDCCBBAA9988
    Execute Command    sysbus WriteDoubleWord 0x10000004 0x11223344
    ${word}=           Execute Command    sysbus ReadQuadWord 0x10000000
    Should Be Equal As Numbers    ${word}    0x11223344BBAA9988

MRAM Partial Write Leaves Corruption
    Create MRAM Machine
    Execute Command    sysbus WriteQuadWord 0x10000000 0xA1A2A3A4A5A6A7A8
    Execute Command    mram_ctrl InjectPartialWrite 0x10000000
    ${word}=           Execute Command    sysbus ReadQuadWord 0x10000000
    Should Not Be Equal As Numbers    ${word}    0xA1A2A3A4A5A6A7A8

NV Read Port Returns Same Data
    Create MRAM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000020 0xDEADBEEF
    ${alias}=          Execute Command    sysbus ReadDoubleWord 0x10080020
    Should Be Equal As Numbers    ${alias}    0xDEADBEEF

NV Read Alias Drops Writes
    Create MRAM Machine
    Execute Command    sysbus WriteDoubleWord 0x10000040 0x12345678
    Execute Command    sysbus WriteDoubleWord 0x10080040 0xFFFFFFFF
    ${original}=       Execute Command    sysbus ReadDoubleWord 0x10000040
    Should Be Equal As Numbers    ${original}    0x12345678
    ${alias}=          Execute Command    sysbus ReadDoubleWord 0x10080040
    Should Be Equal As Numbers    ${alias}    0x12345678
