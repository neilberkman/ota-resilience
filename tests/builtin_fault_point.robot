*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                        ${CURDIR}/..
${BUILTIN_SCENARIO}            vulnerable
${FAULT_AT}                    0
${TOTAL_WRITES}                auto
${RESULT_FILE}                 /tmp/builtin_fault_point.json
${INCLUDE_METADATA_FAULTS}     false
${EVALUATION_MODE}             execute
${PLATFORM_REPL}               ${ROOT}/platforms/cortex_m0_nvm.repl
${VULNERABLE_FIRMWARE_ELF}     ${ROOT}/examples/vulnerable_ota/firmware.elf
${VULNERABLE_STAGING_IMAGE}    ${ROOT}/examples/test_image.bin
${RESILIENT_BOOTLOADER_ELF}    ${ROOT}/examples/resilient_ota/bootloader.elf
${RESILIENT_SLOT_A_BIN}        ${ROOT}/examples/resilient_ota/slot_a.bin
${RESILIENT_SLOT_B_BIN}        ${ROOT}/examples/resilient_ota/slot_b.bin
${RESILIENT_BOOT_META_BIN}     ${ROOT}/examples/resilient_ota/boot_meta.bin

*** Keywords ***
Load Built-In Vulnerable Scenario
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${VULNERABLE_FIRMWARE_ELF}'); bus.LoadBinary(r'${VULNERABLE_STAGING_IMAGE}', 0x10038000)"

Load Built-In Resilient Scenario
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${RESILIENT_BOOTLOADER_ELF}'); bus.LoadBinary(r'${RESILIENT_SLOT_A_BIN}', 0x10002000); bus.LoadBinary(r'${RESILIENT_BOOT_META_BIN}', 0x10070000)"

*** Test Cases ***
Run Built-In Fault Point
    ${default_total_writes}=    Set Variable If    '${BUILTIN_SCENARIO}' == 'vulnerable'    28672    28160
    ${resolved_total_writes}=    Set Variable If    '${TOTAL_WRITES}' == 'auto'    ${default_total_writes}    ${TOTAL_WRITES}

    Execute Command    $repo_root="${ROOT}"
    Execute Command    $fault_at=${FAULT_AT}
    Execute Command    $total_writes=${resolved_total_writes}
    Execute Command    $result_file="${RESULT_FILE}"
    Execute Command    $include_metadata_faults=${INCLUDE_METADATA_FAULTS}
    Execute Command    $evaluation_mode="${EVALUATION_MODE}"
    Execute Command    $slot_b_image="${RESILIENT_SLOT_B_BIN}"

    Run Keyword If    '${BUILTIN_SCENARIO}' == 'vulnerable'    Load Built-In Vulnerable Scenario
    ...    ELSE IF    '${BUILTIN_SCENARIO}' == 'resilient'    Load Built-In Resilient Scenario
    ...    ELSE    Fail    Unsupported BUILTIN_SCENARIO='${BUILTIN_SCENARIO}'

    Run Keyword If    '${BUILTIN_SCENARIO}' == 'vulnerable'    Execute Script    ${ROOT}/scripts/run_vulnerable_fault_point.resc
    ...    ELSE IF    '${BUILTIN_SCENARIO}' == 'resilient'    Execute Script    ${ROOT}/scripts/run_resilient_fault_point.resc
    ...    ELSE    Fail    Unsupported BUILTIN_SCENARIO='${BUILTIN_SCENARIO}'

    File Should Exist    ${RESULT_FILE}
