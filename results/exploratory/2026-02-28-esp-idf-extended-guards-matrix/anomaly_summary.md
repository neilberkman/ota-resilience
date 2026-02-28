# Exploratory Matrix Summary

- Generated: `2026-02-28T060723Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-extended-guards-matrix`
- Cases planned: `4`
- Cases with report: `4`
- Cases missing report: `0`
- Control mismatches: `2`
- Anomalous fault points: `10`
- OtaData drift points (all): `12`
- OtaData benign transitions: `8`
- OtaData allowlisted points: `8`
- OtaData allowlist lanes: `2`
- OtaData suspicious drift points: `4`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 4.159 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "mid"}` | 3 | 3 | 3 |
| 2 | 3.296 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "early"}` | 2 | 2 | 2 |
| 3 | 3.296 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "mid"}` | 2 | 2 | 2 |
| 4 | 2.773 | control_mismatch | `{"actual_control_outcome": "wrong_image", "expected_control_outcome": "success"}` | 1 | 1 | 1 |
| 5 | 2.773 | control_mismatch | `{"actual_control_outcome": "no_boot", "expected_control_outcome": "success"}` | 1 | 1 | 1 |
| 6 | 2.079 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "early"}` | 1 | 1 | 1 |
| 7 | 2.079 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "late"}` | 1 | 1 | 1 |
| 8 | 2.079 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "single"}` | 1 | 1 | 1 |
| 9 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "w", "phase": "early"}` | 1 | 1 | 1 |
| 10 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "w", "phase": "mid"}` | 1 | 1 | 1 |
| 11 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "w", "phase": "late"}` | 1 | 1 | 1 |
| 12 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "e", "phase": "single"}` | 1 | 1 | 1 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 10.900 | `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | `esp_idf_ota_ss_guard__f_profile__c_profile` | `ss_guard` | `profile` | `profile` | +1.000 | +1.000 | +1 | +1.000 |
| 2 | 4.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | `crc_schema_guard` | `profile` | `profile` | +0.000 | +0.000 | +1 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-extended-guards-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-extended-guards-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-extended-guards-matrix/reports/esp_idf_ota_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_ota_ss_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-extended-guards-matrix/reports/esp_idf_ota_ss_guard__f_profile__c_profile.json` |
