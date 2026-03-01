# Exploratory Matrix Summary

- Generated: `2026-03-01T034719Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix`
- Cases planned: `40`
- Cases with report: `40`
- Cases missing report: `0`
- Control mismatches: `12`
- Anomalous fault points: `101`
- OtaData drift points (all): `154`
- OtaData benign transitions: `83`
- OtaData allowlisted points: `83`
- OtaData allowlist lanes: `20`
- OtaData allowlist eligible lanes: `8`
- OtaData allowlist ineligible lanes: `12`
- OtaData allowlist min samples (fault/success): `8/4`
- OtaData suspicious drift points: `71`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 35.156 | control_mismatch | `{"actual_control_outcome": "no_boot", "expected_control_outcome": "success"}` | 8 | 8 | 2 |
| 2 | 25.751 | control_mismatch | `{"actual_control_outcome": "wrong_image", "expected_control_outcome": "success"}` | 4 | 4 | 1 |
| 3 | 14.387 | fault_anomaly | `{"fault_type": "s", "outcome": "no_boot", "phase": "mid"}` | 10 | 10 | 5 |
| 4 | 14.387 | fault_anomaly | `{"fault_type": "d", "outcome": "no_boot", "phase": "early"}` | 10 | 10 | 5 |
| 5 | 14.387 | fault_anomaly | `{"fault_type": "l", "outcome": "no_boot", "phase": "early"}` | 10 | 10 | 5 |
| 6 | 13.183 | fault_anomaly | `{"fault_type": "s", "outcome": "no_boot", "phase": "early"}` | 8 | 8 | 4 |
| 7 | 13.183 | fault_anomaly | `{"fault_type": "d", "outcome": "no_boot", "phase": "mid"}` | 8 | 8 | 4 |
| 8 | 13.183 | fault_anomaly | `{"fault_type": "l", "outcome": "no_boot", "phase": "mid"}` | 8 | 8 | 4 |
| 9 | 13.183 | fault_anomaly | `{"fault_type": "d", "outcome": "no_boot", "phase": "late"}` | 8 | 8 | 4 |
| 10 | 11.675 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "early"}` | 6 | 6 | 3 |
| 11 | 11.675 | fault_anomaly | `{"fault_type": "a", "outcome": "no_boot", "phase": "early"}` | 6 | 6 | 3 |
| 12 | 9.657 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "mid"}` | 4 | 4 | 2 |
| 13 | 9.657 | fault_anomaly | `{"fault_type": "a", "outcome": "no_boot", "phase": "mid"}` | 4 | 4 | 2 |
| 14 | 9.657 | fault_anomaly | `{"fault_type": "s", "outcome": "no_boot", "phase": "late"}` | 4 | 4 | 2 |
| 15 | 9.657 | fault_anomaly | `{"fault_type": "l", "outcome": "no_boot", "phase": "late"}` | 4 | 4 | 2 |
| 16 | 9.657 | fault_anomaly | `{"fault_type": "a", "outcome": "no_boot", "phase": "single"}` | 4 | 4 | 2 |
| 17 | 6.592 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "late"}` | 2 | 2 | 1 |
| 18 | 6.592 | fault_anomaly | `{"fault_type": "a", "outcome": "no_boot", "phase": "late"}` | 2 | 2 | 1 |
| 19 | 6.592 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "single"}` | 2 | 2 | 1 |
| 20 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "s", "phase": "mid"}` | 4 | 4 | 2 |
| 21 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "d", "phase": "early"}` | 4 | 4 | 2 |
| 22 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "l", "phase": "early"}` | 4 | 4 | 2 |
| 23 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "a", "phase": "single"}` | 4 | 4 | 2 |
| 24 | 2.398 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "a", "phase": "single"}` | 10 | 10 | 5 |
| 25 | 2.197 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "single"}` | 8 | 8 | 4 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δcontrol_outcome | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 14.244 | `esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_profile` | `esp_idf_ota_ss_guard__f_write_integrity__c_profile` | `ss_guard` | `write_integrity` | `profile` | +0.889 | +0.889 | +1 | +2 | +0.667 |
| 2 | 14.244 | `esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_otadata_control` | `esp_idf_ota_ss_guard__f_write_integrity__c_otadata_control` | `ss_guard` | `write_integrity` | `otadata_control` | +0.889 | +0.889 | +1 | +2 | +0.667 |
| 3 | 10.600 | `esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_profile` | `esp_idf_ota_ss_guard__f_erase_atomicity__c_profile` | `ss_guard` | `erase_atomicity` | `profile` | +0.500 | +0.500 | +1 | +2 | +0.000 |
| 4 | 10.600 | `esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_otadata_control` | `esp_idf_ota_ss_guard__f_erase_atomicity__c_otadata_control` | `ss_guard` | `erase_atomicity` | `otadata_control` | +0.500 | +0.500 | +1 | +2 | +0.000 |
| 5 | 10.467 | `esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_profile` | `esp_idf_ota_crc_guard__f_write_integrity__c_profile` | `crc_guard` | `write_integrity` | `profile` | +0.333 | +0.333 | +1 | +2 | +0.333 |
| 6 | 10.467 | `esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_otadata_control` | `esp_idf_ota_crc_guard__f_write_integrity__c_otadata_control` | `crc_guard` | `write_integrity` | `otadata_control` | +0.333 | +0.333 | +1 | +2 | +0.333 |
| 7 | 8.000 | `esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_profile` | `esp_idf_ota_crc_guard__f_erase_atomicity__c_profile` | `crc_guard` | `erase_atomicity` | `profile` | +0.000 | +0.000 | +1 | +2 | +0.000 |
| 8 | 8.000 | `esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_otadata_control` | `esp_idf_ota_crc_guard__f_erase_atomicity__c_otadata_control` | `crc_guard` | `erase_atomicity` | `otadata_control` | +0.000 | +0.000 | +1 | +2 | +0.000 |
| 9 | 7.900 | `esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_otadata_control` | `esp_idf_ota_rollback_guard__f_write_integrity__c_otadata_control` | `rollback_guard` | `write_integrity` | `otadata_control` | +1.000 | +1.000 | +0 | +1 | +0.000 |
| 10 | 7.578 | `esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_profile` | `esp_idf_ota_rollback_guard__f_write_integrity__c_profile` | `rollback_guard` | `write_integrity` | `profile` | +0.889 | +1.000 | +0 | +1 | -0.111 |
| 11 | 7.400 | `esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_profile` | `esp_idf_ota_rollback_guard__f_erase_atomicity__c_profile` | `rollback_guard` | `erase_atomicity` | `profile` | +1.000 | +1.000 | +0 | +1 | -1.000 |
| 12 | 7.400 | `esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_otadata_control` | `esp_idf_ota_rollback_guard__f_erase_atomicity__c_otadata_control` | `rollback_guard` | `erase_atomicity` | `otadata_control` | +1.000 | +1.000 | +0 | +1 | -1.000 |
| 13 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_profile` | `esp_idf_ota_crc_schema_guard__f_write_integrity__c_profile` | `crc_schema_guard` | `write_integrity` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 14 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_otadata_control` | `esp_idf_ota_crc_schema_guard__f_write_integrity__c_otadata_control` | `crc_schema_guard` | `write_integrity` | `otadata_control` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 15 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_profile` | `esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_profile` | `crc_schema_guard` | `erase_atomicity` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 16 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_otadata_control` | `esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_otadata_control` | `crc_schema_guard` | `erase_atomicity` | `otadata_control` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 17 | 4.656 | `esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_profile` | `esp_idf_ota_fallback_guard__f_write_integrity__c_profile` | `fallback_guard` | `write_integrity` | `profile` | +0.111 | +0.111 | +0 | +2 | +0.000 |
| 18 | 4.656 | `esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_otadata_control` | `esp_idf_ota_fallback_guard__f_write_integrity__c_otadata_control` | `fallback_guard` | `write_integrity` | `otadata_control` | +0.111 | +0.111 | +0 | +2 | +0.000 |
| 19 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_profile` | `esp_idf_ota_fallback_guard__f_erase_atomicity__c_profile` | `fallback_guard` | `erase_atomicity` | `profile` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 20 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_otadata_control` | `esp_idf_ota_fallback_guard__f_erase_atomicity__c_otadata_control` | `fallback_guard` | `erase_atomicity` | `otadata_control` | +0.000 | +0.000 | +0 | +2 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_ota_crc_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_guard__f_write_integrity__c_profile.json` |
| `esp_idf_ota_crc_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_ota_crc_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_ota_crc_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_ota_crc_schema_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_schema_guard__f_write_integrity__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_schema_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_crc_schema_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_ota_fallback_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_fallback_guard__f_write_integrity__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_fallback_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_ota_fallback_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_fallback_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_fallback_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_ota_rollback_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_rollback_guard__f_write_integrity__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_rollback_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_ota_rollback_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_rollback_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_rollback_guard__f_erase_atomicity__c_otadata_control.json` |
| `esp_idf_ota_ss_guard__f_write_integrity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_ss_guard__f_write_integrity__c_profile.json` |
| `esp_idf_ota_ss_guard__f_write_integrity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_ss_guard__f_write_integrity__c_otadata_control.json` |
| `esp_idf_ota_ss_guard__f_erase_atomicity__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_ss_guard__f_erase_atomicity__c_profile.json` |
| `esp_idf_ota_ss_guard__f_erase_atomicity__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-03-01-esp-idf-write-integrity-erase-atomicity-matrix/reports/esp_idf_ota_ss_guard__f_erase_atomicity__c_otadata_control.json` |
