*** Settings ***
Library    OperatingSystem

*** Variables ***
${ROOT}                 ${CURDIR}/..
${ROLLBACK_RESULT}      /tmp/trial_boot_result.json
${CONFIRM_RESULT}       /tmp/trial_boot_confirm_result.json
${FALLBACK_REPAIR_RESULT}    /tmp/fallback_self_heal_result.json

*** Test Cases ***
Trial Boot Reverts To Slot A After Failed Self-Test
    Run Keyword And Ignore Error    Remove File    ${ROLLBACK_RESULT}

    Execute Command    $repo_root="${ROOT}"
    Execute Command    $boot_cycles=6
    Execute Command    $result_file="${ROLLBACK_RESULT}"
    Execute Script    ${ROOT}/scripts/run_trial_boot_fault_point.resc

    File Should Exist    ${ROLLBACK_RESULT}
    ${result}=          Evaluate    json.load(open(r'''${ROLLBACK_RESULT}''', 'r', encoding='utf-8'))    modules=json
    Should Be Equal     ${result["boot_outcome"]}    success
    Should Be Equal     ${result["final_slot"]}    A
    Should Be True      ${result["reverted"]}
    Should Be True      ${result["boot_cycles"]} >= 4

Trial Boot Confirms Slot B And Stays Active
    Run Keyword And Ignore Error    Remove File    ${CONFIRM_RESULT}

    Execute Command    $repo_root="${ROOT}"
    Execute Command    $boot_cycles=6
    Execute Command    $slot_b_image="examples/resilient_ota/slot_b.bin"
    Execute Command    $result_file="${CONFIRM_RESULT}"
    Execute Script    ${ROOT}/scripts/run_trial_boot_fault_point.resc

    File Should Exist    ${CONFIRM_RESULT}
    ${result}=          Evaluate    json.load(open(r'''${CONFIRM_RESULT}''', 'r', encoding='utf-8'))    modules=json
    Should Be Equal     ${result["boot_outcome"]}    success
    Should Be Equal     ${result["final_slot"]}    B
    Should Be True      ${result["confirmed"]}
    Should Be True      ${result["stable_after_reset"]}
    Should Be Equal     ${result["reverted"]}    ${False}

Fallback To Other Slot Repairs Metadata
    Run Keyword And Ignore Error    Remove File    ${FALLBACK_REPAIR_RESULT}

    Execute Command    $repo_root="${ROOT}"
    Execute Command    $result_file="${FALLBACK_REPAIR_RESULT}"
    Execute Script    ${ROOT}/scripts/run_fallback_self_heal.resc

    File Should Exist    ${FALLBACK_REPAIR_RESULT}
    ${result}=          Evaluate    json.load(open(r'''${FALLBACK_REPAIR_RESULT}''', 'r', encoding='utf-8'))    modules=json
    Should Be Equal     ${result["boot_outcome"]}    success
    Should Be Equal     ${result["final_slot"]}    B
    Should Be True      ${result["repaired"]}
