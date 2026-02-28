# Exploratory Matrix Summary

- Generated: `2026-02-28T042854Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-rollback-guard-matrix-v2`
- Cases planned: `2`
- Cases with report: `2`
- Cases missing report: `0`
- Control mismatches: `0`
- Anomalous fault points: `5`
- OtaData drift points (all): `4`
- OtaData benign transitions: `4`
- OtaData allowlisted points: `4`
- OtaData suspicious drift points: `0`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 2.079 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "mid"}` | 1 | 1 | 1 |
| 2 | 2.079 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "late"}` | 1 | 1 | 1 |
| 3 | 2.079 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "early"}` | 1 | 1 | 1 |
| 4 | 2.079 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "late"}` | 1 | 1 | 1 |
| 5 | 1.386 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "early"}` | 1 | 1 | 1 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 5.100 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile` | `esp_idf_ota_rollback_guard__f_profile__c_profile` | `rollback_guard` | `profile` | `profile` | +1.000 | +0.800 | +0 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-rollback-guard-matrix-v2/reports/esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-rollback-guard-matrix-v2/reports/esp_idf_ota_rollback_guard__f_profile__c_profile.json` |
