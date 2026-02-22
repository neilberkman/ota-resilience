*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                        ${CURDIR}/..
${SCENARIO}                    vulnerable
${FAULT_AT}                    0
${TOTAL_WRITES}                28672
${RESULT_FILE}                 /tmp/ota_fault_point.json
${INCLUDE_METADATA_FAULTS}     false

*** Keywords ***
Load Vulnerable Scenario
    Execute Command    include "${ROOT}/peripherals/MRAMController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${ROOT}/platforms/cortex_m0_mram.repl
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${ROOT}/examples/vulnerable_ota/firmware.elf'); bus.LoadBinary(r'${ROOT}/examples/test_image.bin', 0x10038000)"

Load Resilient Scenario
    Execute Command    include "${ROOT}/peripherals/MRAMController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${ROOT}/platforms/cortex_m0_mram.repl
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${ROOT}/examples/resilient_ota/bootloader.elf'); bus.LoadBinary(r'${ROOT}/examples/resilient_ota/slot_a.bin', 0x10002000); bus.LoadBinary(r'${ROOT}/examples/resilient_ota/boot_meta.bin', 0x10070000)"

*** Test Cases ***
Run OTA Fault Point
    Execute Command    $repo_root="${ROOT}"
    Execute Command    $fault_at=${FAULT_AT}
    Execute Command    $total_writes=${TOTAL_WRITES}
    Execute Command    $result_file="${RESULT_FILE}"
    Execute Command    $include_metadata_faults=${INCLUDE_METADATA_FAULTS}

    Run Keyword If    '${SCENARIO}' == 'vulnerable'    Load Vulnerable Scenario
    ...    ELSE IF    '${SCENARIO}' == 'resilient'    Load Resilient Scenario
    ...    ELSE    Fail    Unsupported SCENARIO='${SCENARIO}'

    Run Keyword If    '${SCENARIO}' == 'vulnerable'    Execute Script    ${ROOT}/scripts/run_vulnerable_fault_point.resc
    ...    ELSE IF    '${SCENARIO}' == 'resilient'    Execute Script    ${ROOT}/scripts/run_resilient_fault_point.resc
    ...    ELSE    Fail    Unsupported SCENARIO='${SCENARIO}'

    File Should Exist    ${RESULT_FILE}
