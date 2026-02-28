# Exploratory Matrix Summary

- Generated: `2026-02-28T072529Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-otadata-control-preset-smoke`
- Cases planned: `4`
- Cases with report: `4`
- Cases missing report: `0`
- Control mismatches: `1`
- Anomalous fault points: `10`
- OtaData drift points (all): `8`
- OtaData benign transitions: `8`
- OtaData allowlisted points: `8`
- OtaData allowlist lanes: `2`
- OtaData suspicious drift points: `0`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 4.159 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "mid"}` | 3 | 3 | 3 |
| 2 | 4.159 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "early"}` | 3 | 3 | 3 |
| 3 | 3.296 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "mid"}` | 2 | 2 | 2 |
| 4 | 2.773 | control_mismatch | `{"actual_control_outcome": "wrong_image", "expected_control_outcome": "success"}` | 1 | 1 | 1 |
| 5 | 2.079 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "late"}` | 1 | 1 | 1 |
| 6 | 2.079 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "late"}` | 1 | 1 | 1 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 6.400 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_otadata_control` | `esp_idf_ota_rollback_guard__f_profile__c_otadata_control` | `rollback_guard` | `profile` | `otadata_control` | +0.800 | +0.800 | +0 | +0.000 |
| 2 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_otadata_control` | `esp_idf_ota_crc_schema_guard__f_profile__c_otadata_control` | `crc_schema_guard` | `profile` | `otadata_control` | +0.000 | +0.000 | +1 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-otadata-control-preset-smoke/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_otadata_control.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_profile__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-otadata-control-preset-smoke/reports/esp_idf_fault_no_abort_rollback_guard__f_profile__c_otadata_control.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-otadata-control-preset-smoke/reports/esp_idf_ota_crc_schema_guard__f_profile__c_otadata_control.json` |
| `esp_idf_ota_rollback_guard__f_profile__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-otadata-control-preset-smoke/reports/esp_idf_ota_rollback_guard__f_profile__c_otadata_control.json` |
