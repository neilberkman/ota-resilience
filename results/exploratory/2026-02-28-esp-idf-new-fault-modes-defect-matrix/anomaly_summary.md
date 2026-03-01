# Exploratory Matrix Summary

- Generated: `2026-03-01T032503Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix`
- Cases planned: `40`
- Cases with report: `40`
- Cases missing report: `0`
- Control mismatches: `12`
- Anomalous fault points: `29`
- OtaData drift points (all): `82`
- OtaData benign transitions: `72`
- OtaData allowlisted points: `72`
- OtaData allowlist lanes: `20`
- OtaData suspicious drift points: `10`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 35.156 | control_mismatch | `{"actual_control_outcome": "no_boot", "expected_control_outcome": "success"}` | 8 | 8 | 2 |
| 2 | 25.751 | control_mismatch | `{"actual_control_outcome": "wrong_image", "expected_control_outcome": "success"}` | 4 | 4 | 1 |
| 3 | 14.387 | fault_anomaly | `{"fault_type": "r", "outcome": "no_boot", "phase": "mid"}` | 10 | 10 | 5 |
| 4 | 9.657 | fault_anomaly | `{"fault_type": "r", "outcome": "no_boot", "phase": "late"}` | 4 | 4 | 2 |
| 5 | 9.657 | fault_anomaly | `{"fault_type": "t", "outcome": "no_boot", "phase": "early"}` | 4 | 4 | 2 |
| 6 | 9.657 | fault_anomaly | `{"fault_type": "t", "outcome": "no_boot", "phase": "mid"}` | 4 | 4 | 2 |
| 7 | 9.657 | fault_anomaly | `{"fault_type": "t", "outcome": "no_boot", "phase": "late"}` | 4 | 4 | 2 |
| 8 | 6.592 | fault_anomaly | `{"fault_type": "r", "outcome": "no_boot", "phase": "early"}` | 2 | 2 | 1 |
| 9 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "r", "phase": "mid"}` | 4 | 4 | 2 |
| 10 | 1.648 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "r", "phase": "early"}` | 2 | 2 | 1 |
| 11 | 1.648 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "r", "phase": "late"}` | 2 | 2 | 1 |
| 12 | 1.386 | fault_anomaly | `{"fault_type": "r", "outcome": "wrong_image", "phase": "early"}` | 1 | 1 | 1 |
| 13 | 1.099 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "r", "phase": "early"}` | 2 | 2 | 1 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δcontrol_outcome | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 14.800 | `esp_idf_fault_single_sector_ss_guard__f_write_reject__c_profile` | `esp_idf_ota_ss_guard__f_write_reject__c_profile` | `ss_guard` | `write_reject` | `profile` | +1.000 | +1.000 | +1 | +2 | +1.000 |
| 2 | 14.800 | `esp_idf_fault_single_sector_ss_guard__f_write_reject__c_otadata_control` | `esp_idf_ota_ss_guard__f_write_reject__c_otadata_control` | `ss_guard` | `write_reject` | `otadata_control` | +1.000 | +1.000 | +1 | +2 | +1.000 |
| 3 | 13.300 | `esp_idf_fault_single_sector_ss_guard__f_time_reset__c_profile` | `esp_idf_ota_ss_guard__f_time_reset__c_profile` | `ss_guard` | `time_reset` | `profile` | +1.000 | +1.000 | +1 | +2 | +0.000 |
| 4 | 13.300 | `esp_idf_fault_single_sector_ss_guard__f_time_reset__c_otadata_control` | `esp_idf_ota_ss_guard__f_time_reset__c_otadata_control` | `ss_guard` | `time_reset` | `otadata_control` | +1.000 | +1.000 | +1 | +2 | +0.000 |
| 5 | 10.767 | `esp_idf_fault_no_crc_crc_guard__f_write_reject__c_profile` | `esp_idf_ota_crc_guard__f_write_reject__c_profile` | `crc_guard` | `write_reject` | `profile` | +0.333 | +0.333 | +1 | +2 | +0.667 |
| 6 | 10.767 | `esp_idf_fault_no_crc_crc_guard__f_write_reject__c_otadata_control` | `esp_idf_ota_crc_guard__f_write_reject__c_otadata_control` | `crc_guard` | `write_reject` | `otadata_control` | +0.333 | +0.333 | +1 | +2 | +0.667 |
| 7 | 8.000 | `esp_idf_fault_no_crc_crc_guard__f_time_reset__c_profile` | `esp_idf_ota_crc_guard__f_time_reset__c_profile` | `crc_guard` | `time_reset` | `profile` | +0.000 | +0.000 | +1 | +2 | +0.000 |
| 8 | 8.000 | `esp_idf_fault_no_crc_crc_guard__f_time_reset__c_otadata_control` | `esp_idf_ota_crc_guard__f_time_reset__c_otadata_control` | `crc_guard` | `time_reset` | `otadata_control` | +0.000 | +0.000 | +1 | +2 | +0.000 |
| 9 | 7.300 | `esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_profile` | `esp_idf_ota_rollback_guard__f_time_reset__c_profile` | `rollback_guard` | `time_reset` | `profile` | +1.000 | +1.000 | +0 | +1 | +0.000 |
| 10 | 7.300 | `esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_otadata_control` | `esp_idf_ota_rollback_guard__f_time_reset__c_otadata_control` | `rollback_guard` | `time_reset` | `otadata_control` | +1.000 | +1.000 | +0 | +1 | +0.000 |
| 11 | 6.633 | `esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_profile` | `esp_idf_ota_rollback_guard__f_write_reject__c_profile` | `rollback_guard` | `write_reject` | `profile` | +1.000 | +0.667 | +0 | +1 | +0.000 |
| 12 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_profile` | `esp_idf_ota_crc_schema_guard__f_write_reject__c_profile` | `crc_schema_guard` | `write_reject` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 13 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_otadata_control` | `esp_idf_ota_crc_schema_guard__f_write_reject__c_otadata_control` | `crc_schema_guard` | `write_reject` | `otadata_control` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 14 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_profile` | `esp_idf_ota_crc_schema_guard__f_time_reset__c_profile` | `crc_schema_guard` | `time_reset` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 15 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_otadata_control` | `esp_idf_ota_crc_schema_guard__f_time_reset__c_otadata_control` | `crc_schema_guard` | `time_reset` | `otadata_control` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 16 | 5.533 | `esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_otadata_control` | `esp_idf_ota_rollback_guard__f_write_reject__c_otadata_control` | `rollback_guard` | `write_reject` | `otadata_control` | +0.667 | +0.667 | +0 | +1 | +0.000 |
| 17 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_profile` | `esp_idf_ota_fallback_guard__f_write_reject__c_profile` | `fallback_guard` | `write_reject` | `profile` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 18 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_otadata_control` | `esp_idf_ota_fallback_guard__f_write_reject__c_otadata_control` | `fallback_guard` | `write_reject` | `otadata_control` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 19 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_profile` | `esp_idf_ota_fallback_guard__f_time_reset__c_profile` | `fallback_guard` | `time_reset` | `profile` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 20 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_otadata_control` | `esp_idf_ota_fallback_guard__f_time_reset__c_otadata_control` | `fallback_guard` | `time_reset` | `otadata_control` | +0.000 | +0.000 | +0 | +2 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_abort_rollback_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_write_reject__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_fault_no_crc_crc_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_time_reset__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_crc_crc_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_write_reject__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_fault_single_sector_ss_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_time_reset__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_fault_single_sector_ss_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_ota_crc_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_guard__f_write_reject__c_profile.json` |
| `esp_idf_ota_crc_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_ota_crc_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_guard__f_time_reset__c_profile.json` |
| `esp_idf_ota_crc_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_ota_crc_schema_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_schema_guard__f_write_reject__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_schema_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_ota_crc_schema_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_schema_guard__f_time_reset__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_crc_schema_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_ota_fallback_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_fallback_guard__f_write_reject__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_fallback_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_ota_fallback_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_fallback_guard__f_time_reset__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_fallback_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_ota_rollback_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_rollback_guard__f_write_reject__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_rollback_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_ota_rollback_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_rollback_guard__f_time_reset__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_rollback_guard__f_time_reset__c_otadata_control.json` |
| `esp_idf_ota_ss_guard__f_write_reject__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_ss_guard__f_write_reject__c_profile.json` |
| `esp_idf_ota_ss_guard__f_write_reject__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_ss_guard__f_write_reject__c_otadata_control.json` |
| `esp_idf_ota_ss_guard__f_time_reset__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_ss_guard__f_time_reset__c_profile.json` |
| `esp_idf_ota_ss_guard__f_time_reset__c_otadata_control` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-new-fault-modes-defect-matrix/reports/esp_idf_ota_ss_guard__f_time_reset__c_otadata_control.json` |
