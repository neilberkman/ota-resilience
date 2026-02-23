*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                        ${CURDIR}/..
${FAULT_SEQUENCE}              100,5000
${TOTAL_WRITES}                28160
${RESULT_FILE}                 /tmp/ota_multi_fault.json
${INCLUDE_METADATA_FAULTS}     false
${EVALUATION_MODE}             execute
${PLATFORM_REPL}               ${ROOT}/platforms/cortex_m0_nvm.repl
${RESILIENT_BOOTLOADER_ELF}    ${ROOT}/examples/resilient_ota/bootloader.elf
${RESILIENT_SLOT_A_BIN}        ${ROOT}/examples/resilient_ota/slot_a.bin
${RESILIENT_SLOT_B_BIN}        ${ROOT}/examples/resilient_ota/slot_b.bin
${RESILIENT_BOOT_META_BIN}     ${ROOT}/examples/resilient_ota/boot_meta.bin
${SCENARIO_LOADER_SCRIPT}      ${EMPTY}

*** Keywords ***
Load Resilient Scenario
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${RESILIENT_BOOTLOADER_ELF}'); bus.LoadBinary(r'${RESILIENT_SLOT_A_BIN}', 0x10002000); bus.LoadBinary(r'${RESILIENT_BOOT_META_BIN}', 0x10070000)"

*** Test Cases ***
Run Multi-Fault Resilient OTA
    Execute Command    $repo_root="${ROOT}"
    Execute Command    $fault_sequence="${FAULT_SEQUENCE}"
    Execute Command    $total_writes=${TOTAL_WRITES}
    Execute Command    $result_file="${RESULT_FILE}"
    Execute Command    $include_metadata_faults=${INCLUDE_METADATA_FAULTS}
    Execute Command    $evaluation_mode="${EVALUATION_MODE}"
    Execute Command    $slot_b_image="${RESILIENT_SLOT_B_BIN}"

    Run Keyword If    '${SCENARIO_LOADER_SCRIPT}' != ''    Execute Script    ${SCENARIO_LOADER_SCRIPT}
    ...    ELSE    Load Resilient Scenario

    Execute Script    ${ROOT}/scripts/run_resilient_multi_fault.resc

    File Should Exist    ${RESULT_FILE}
