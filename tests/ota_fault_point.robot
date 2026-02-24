*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                        ${CURDIR}/..
${SCENARIO}                    vulnerable
${FAULT_AT}                    0
${TOTAL_WRITES}                auto
${RESULT_FILE}                 /tmp/ota_fault_point.json
${INCLUDE_METADATA_FAULTS}     false
${EVALUATION_MODE}             execute
${PLATFORM_REPL}               ${ROOT}/platforms/cortex_m0_nvm.repl
${VULNERABLE_FIRMWARE_ELF}     ${ROOT}/examples/vulnerable_ota/firmware.elf
${VULNERABLE_STAGING_IMAGE}    ${ROOT}/examples/vulnerable_ota/firmware.bin
${RESILIENT_BOOTLOADER_ELF}    ${ROOT}/examples/resilient_ota/bootloader.elf
${RESILIENT_SLOT_A_BIN}        ${ROOT}/examples/resilient_ota/slot_a.bin
${RESILIENT_SLOT_B_BIN}        ${ROOT}/examples/resilient_ota/slot_b.bin
${RESILIENT_BOOT_META_BIN}     ${ROOT}/examples/resilient_ota/boot_meta.bin
${SCENARIO_LOADER_SCRIPT}      ${EMPTY}
${FAULT_POINT_SCRIPT}          ${EMPTY}

# Runtime fault sweep variables (profile-driven mode).
${RUNTIME_MODE}                false
${CALIBRATION_MODE}            false
${BOOTLOADER_ELF}              ${EMPTY}
${BOOTLOADER_ENTRY}            0x10000000
${SRAM_START}                  0x20000000
${SRAM_END}                    0x20020000
${WRITE_GRANULARITY}           8
${RUN_DURATION}                0.5
${MAX_WRITES_CAP}              100000
${SLOT_EXEC_BASE}              0x10002000
${SLOT_EXEC_SIZE}              0x37000
${SLOT_STAGING_BASE}           0x10039000
${SLOT_STAGING_SIZE}           0x37000
${IMAGE_EXEC}                  ${EMPTY}
${IMAGE_STAGING}               ${EMPTY}
${PRE_BOOT_STATE_BIN}          ${EMPTY}
${SETUP_SCRIPT}                ${EMPTY}
${SUCCESS_VTOR_SLOT}           exec
${SUCCESS_PC_SLOT}             ${EMPTY}
${SUCCESS_MARKER_ADDR}         0
${SUCCESS_MARKER_VALUE}        0
${FAULT_POINTS_CSV}            ${EMPTY}
${IMAGE_STAGING_PATH}          ${EMPTY}
${IMAGE_EXEC_PATH}             ${EMPTY}

*** Keywords ***
Load Vulnerable Scenario
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${VULNERABLE_FIRMWARE_ELF}'); bus.LoadBinary(r'${VULNERABLE_STAGING_IMAGE}', 0x10038000)"

Load Resilient Scenario
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadELF(r'${RESILIENT_BOOTLOADER_ELF}'); bus.LoadBinary(r'${RESILIENT_SLOT_A_BIN}', 0x10002000); bus.LoadBinary(r'${RESILIENT_BOOT_META_BIN}', 0x10070000)"

Load Runtime Scenario
    [Documentation]    Profile-driven runtime scenario: load peripheral, platform, ELF, and seed images.
    Execute Command    include "${ROOT}/peripherals/NVMemoryController.cs"
    Execute Command    include "${ROOT}/peripherals/NRF52NVMC.cs"
    Execute Command    mach create
    Execute Command    machine LoadPlatformDescription @${PLATFORM_REPL}
    ${load_cmds}=    Set Variable    bus=monitor.Machine.SystemBus; bus.LoadELF(r'${BOOTLOADER_ELF}')
    Run Keyword If    '${IMAGE_EXEC}' != ''    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadBinary(r'${IMAGE_EXEC}', ${SLOT_EXEC_BASE})"
    Run Keyword If    '${IMAGE_STAGING}' != ''    Execute Command    python "bus=monitor.Machine.SystemBus; bus.LoadBinary(r'${IMAGE_STAGING}', ${SLOT_STAGING_BASE})"
    Execute Command    python "${load_cmds}"

*** Test Cases ***
Run OTA Fault Point
    # Runtime sweep mode (profile-driven).
    Run Keyword If    '${RUNTIME_MODE}' == 'true'    Run Runtime Fault Point
    ...    ELSE    Run Classic Fault Point

*** Keywords ***
Run Classic Fault Point
    ${default_total_writes}=    Set Variable If    '${SCENARIO}' == 'vulnerable'    28672    28160
    ${resolved_total_writes}=    Set Variable If    '${TOTAL_WRITES}' == 'auto'    ${default_total_writes}    ${TOTAL_WRITES}

    Execute Command    $repo_root="${ROOT}"
    Execute Command    $fault_at=${FAULT_AT}
    Execute Command    $total_writes=${resolved_total_writes}
    Execute Command    $result_file="${RESULT_FILE}"
    Execute Command    $include_metadata_faults=${INCLUDE_METADATA_FAULTS}
    Execute Command    $evaluation_mode="${EVALUATION_MODE}"
    Execute Command    $slot_b_image="${RESILIENT_SLOT_B_BIN}"

    Run Keyword If    '${SCENARIO}' == 'vulnerable'    Load Vulnerable Scenario
    ...    ELSE IF    '${SCENARIO}' == 'resilient'    Load Resilient Scenario
    ...    ELSE IF    '${SCENARIO_LOADER_SCRIPT}' != ''    Execute Script    ${SCENARIO_LOADER_SCRIPT}
    ...    ELSE    Fail    Unsupported SCENARIO='${SCENARIO}'. Provide SCENARIO_LOADER_SCRIPT and FAULT_POINT_SCRIPT for custom scenarios.

    Run Keyword If    '${SCENARIO}' == 'vulnerable'    Execute Script    ${ROOT}/scripts/run_vulnerable_fault_point.resc
    ...    ELSE IF    '${SCENARIO}' == 'resilient'    Execute Script    ${ROOT}/scripts/run_resilient_fault_point.resc
    ...    ELSE IF    '${FAULT_POINT_SCRIPT}' != ''    Execute Script    ${FAULT_POINT_SCRIPT}
    ...    ELSE    Fail    Missing FAULT_POINT_SCRIPT for custom SCENARIO='${SCENARIO}'

    File Should Exist    ${RESULT_FILE}

Run Runtime Fault Point
    [Documentation]    Profile-driven runtime fault sweep. Uses run_runtime_fault_sweep.resc.
    Load Runtime Scenario

    # Set all monitor variables for the .resc script.
    Execute Command    $repo_root="${ROOT}"
    Execute Command    $fault_at=${FAULT_AT}
    Execute Command    $result_file="${RESULT_FILE}"
    Execute Command    $calibration_mode=${CALIBRATION_MODE}
    Execute Command    $evaluation_mode="${EVALUATION_MODE}"
    Execute Command    $run_duration="${RUN_DURATION}"
    Execute Command    $max_writes_cap=${MAX_WRITES_CAP}
    Execute Command    $bootloader_elf="${BOOTLOADER_ELF}"
    Execute Command    $bootloader_entry=${BOOTLOADER_ENTRY}
    Execute Command    $sram_start=${SRAM_START}
    Execute Command    $sram_end=${SRAM_END}
    Execute Command    $slot_exec_base=${SLOT_EXEC_BASE}
    Execute Command    $slot_exec_size=${SLOT_EXEC_SIZE}
    Execute Command    $slot_staging_base=${SLOT_STAGING_BASE}
    Execute Command    $slot_staging_size=${SLOT_STAGING_SIZE}
    Execute Command    $pre_boot_state_bin="${PRE_BOOT_STATE_BIN}"
    Execute Command    $setup_script="${SETUP_SCRIPT}"
    Execute Command    $success_vtor_slot="${SUCCESS_VTOR_SLOT}"
    Execute Command    $success_pc_slot="${SUCCESS_PC_SLOT}"
    Execute Command    $success_marker_addr=${SUCCESS_MARKER_ADDR}
    Execute Command    $success_marker_value=${SUCCESS_MARKER_VALUE}
    Execute Command    $fault_points_csv="${FAULT_POINTS_CSV}"
    Execute Command    $image_staging_path="${IMAGE_STAGING_PATH}"
    Execute Command    $image_exec_path="${IMAGE_EXEC_PATH}"

    Execute Script    ${ROOT}/scripts/run_runtime_fault_sweep.resc

    File Should Exist    ${RESULT_FILE}
