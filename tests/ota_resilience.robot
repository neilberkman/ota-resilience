*** Settings ***
Library    Process
Library    OperatingSystem
Library    Collections

*** Variables ***
${ROOT}    ${CURDIR}/..

*** Test Cases ***
Vulnerable OTA Bricks On Power Loss During Copy
    ${result}=    Run Process    python3    scripts/ota_fault_campaign.py    --scenario    vulnerable    --fault-range    0:28672    --fault-step    28672    --output    results/vulnerable_campaign.json    cwd=${ROOT}
    Should Be Equal As Integers    ${result.rc}    0
    ${report}=    Evaluate    json.load(open(r'''${ROOT}/results/vulnerable_campaign.json''', 'r', encoding='utf-8'))    modules=json
    ${outcomes}=    Evaluate    [entry["boot_outcome"] for entry in $report["results"]["vulnerable"]]
    List Should Contain Value    ${outcomes}    hard_fault

Resilient OTA Recovers From Power Loss During Write
    ${result}=    Run Process    python3    scripts/ota_fault_campaign.py    --scenario    resilient    --fault-range    0:20000    --fault-step    20000    --output    results/resilient_campaign.json    cwd=${ROOT}
    Should Be Equal As Integers    ${result.rc}    0
    ${report}=    Evaluate    json.load(open(r'''${ROOT}/results/resilient_campaign.json''', 'r', encoding='utf-8'))    modules=json
    ${outcomes}=    Evaluate    [entry["boot_outcome"] for entry in $report["results"]["resilient"]]
    List Should Not Contain Value    ${outcomes}    hard_fault

Resilient OTA Recovers From Power Loss During Metadata Update
    ${result}=    Run Process    python3    scripts/ota_fault_campaign.py    --scenario    resilient    --include-metadata-faults    --fault-range    28672:28736    --fault-step    32    --output    results/resilient_meta_campaign.json    cwd=${ROOT}
    Should Be Equal As Integers    ${result.rc}    0
    ${report}=    Evaluate    json.load(open(r'''${ROOT}/results/resilient_meta_campaign.json''', 'r', encoding='utf-8'))    modules=json
    ${outcomes}=    Evaluate    [entry["boot_outcome"] for entry in $report["results"]["resilient"]]
    List Should Not Contain Value    ${outcomes}    hard_fault
    ${meta_faults_enabled}=    Evaluate    bool($report["include_metadata_faults"])
    Should Be True    ${meta_faults_enabled}

Resilient OTA Full Campaign
    ${result}=    Run Process    python3    scripts/ota_fault_campaign.py    --scenario    comparative    --fault-range    0:28672    --fault-step    14336    --output    results/full_campaign.json    cwd=${ROOT}
    Should Be Equal As Integers    ${result.rc}    0
    ${report}=    Evaluate    json.load(open(r'''${ROOT}/results/full_campaign.json''', 'r', encoding='utf-8'))    modules=json
    ${resilient_brick_rate}=    Evaluate    float($report["summary"]["resilient"]["brick_rate"])
    ${vulnerable_bricks}=    Evaluate    int($report["summary"]["vulnerable"]["bricks"])
    Should Be Equal As Numbers    ${resilient_brick_rate}    0.0
    Should Be True    ${vulnerable_bricks} > 0
