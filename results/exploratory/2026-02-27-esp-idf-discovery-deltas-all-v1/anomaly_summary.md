# Exploratory Matrix Summary

- Generated: `2026-02-28T061632Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1`
- Cases planned: `68`
- Cases with report: `68`
- Cases missing report: `0`
- Control mismatches: `10`
- Anomalous fault points: `57`
- OtaData drift points (all): `228`
- OtaData benign transitions: `191`
- OtaData allowlisted points: `191`
- OtaData allowlist lanes: `28`
- OtaData suspicious drift points: `37`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 15.567 | control_mismatch | `{"actual_control_outcome": "no_boot", "expected_control_outcome": "success"}` | 6 | 6 | 3 |
| 2 | 14.387 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "mid"}` | 10 | 10 | 5 |
| 3 | 11.675 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "early"}` | 6 | 6 | 3 |
| 4 | 9.657 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "mid"}` | 4 | 4 | 2 |
| 5 | 9.657 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "early"}` | 4 | 4 | 2 |
| 6 | 9.657 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "late"}` | 4 | 4 | 2 |
| 7 | 8.789 | control_mismatch | `{"actual_control_outcome": "wrong_image", "expected_control_outcome": "success"}` | 2 | 2 | 1 |
| 8 | 8.789 | control_mismatch | `{"actual_control_outcome": "success", "expected_control_outcome": "wrong_image"}` | 2 | 2 | 1 |
| 9 | 6.592 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "late"}` | 2 | 2 | 1 |
| 10 | 6.592 | fault_anomaly | `{"fault_type": "e", "outcome": "no_boot", "phase": "single"}` | 2 | 2 | 1 |
| 11 | 5.375 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "early"}` | 5 | 5 | 5 |
| 12 | 5.375 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "mid"}` | 5 | 5 | 5 |
| 13 | 4.394 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 14 | 4.394 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 15 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 16 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 17 | 4.394 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 18 | 4.159 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "mid"}` | 3 | 3 | 2 |
| 19 | 3.296 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "late"}` | 2 | 2 | 2 |
| 20 | 3.219 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "w", "phase": "late"}` | 4 | 4 | 1 |
| 21 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "late"}` | 4 | 4 | 1 |
| 22 | 3.219 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "b", "phase": "late"}` | 4 | 4 | 1 |
| 23 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "w", "phase": "early"}` | 4 | 4 | 1 |
| 24 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "single"}` | 4 | 4 | 1 |
| 25 | 2.414 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "w", "phase": "mid"}` | 4 | 4 | 2 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 11.200 | `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_ss_guard__f_write_erase_bit__c_profile` | `ss_guard` | `write_erase_bit` | `profile` | +1.000 | +1.000 | +1 | +1.000 |
| 2 | 10.900 | `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | `esp_idf_ota_ss_guard__f_profile__c_profile` | `ss_guard` | `profile` | `profile` | +1.000 | +1.000 | +1 | +1.000 |
| 3 | 7.514 | `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | `crc_guard` | `write_erase_bit` | `profile` | +0.429 | +0.429 | +1 | +0.714 |
| 4 | 6.475 | `esp_idf_fault_no_crc_crc_guard__f_profile__c_profile` | `esp_idf_ota_crc_guard__f_profile__c_profile` | `crc_guard` | `profile` | `profile` | +0.250 | +0.250 | +1 | +0.750 |
| 5 | 5.100 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile` | `esp_idf_ota_rollback_guard__f_profile__c_profile` | `rollback_guard` | `profile` | `profile` | +1.000 | +0.800 | +0 | +0.000 |
| 6 | 5.100 | `esp_idf_fault_no_abort__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.200 | +0.200 | +1 | +0.000 |
| 7 | 5.039 | `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_rollback_guard__f_write_erase_bit__c_profile` | `rollback_guard` | `write_erase_bit` | `profile` | +0.857 | +0.875 | +0 | -0.143 |
| 8 | 4.725 | `esp_idf_fault_no_abort__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.125 | +0.125 | +1 | +0.000 |
| 9 | 4.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | `crc_schema_guard` | `profile` | `profile` | +0.000 | +0.000 | +1 | +0.000 |
| 10 | 4.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile` | `crc_schema_guard` | `write_erase_bit` | `profile` | +0.000 | +0.000 | +1 | +0.000 |
| 11 | 4.000 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_image_hash_exec` | `esp_idf_ota_rollback_guard__f_profile__c_image_hash_exec` | `rollback_guard` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +1 | +0.000 |
| 12 | 4.000 | `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_image_hash_exec` | `esp_idf_ota_rollback_guard__f_write_erase_bit__c_image_hash_exec` | `rollback_guard` | `write_erase_bit` | `image_hash_exec` | +0.000 | +0.000 | +1 | +0.000 |
| 13 | 2.167 | `esp_idf_fault_no_crc__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.556 | +0.000 | +0 | +0.000 |
| 14 | 2.167 | `esp_idf_fault_no_crc__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.556 | +0.000 | +0 | +0.000 |
| 15 | 0.000 | `esp_idf_fault_no_crc_crc_guard__f_profile__c_image_hash_exec` | `esp_idf_ota_crc_guard__f_profile__c_image_hash_exec` | `crc_guard` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +0 | +0.500 |
| 16 | 0.000 | `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_image_hash_exec` | `esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec` | `crc_guard` | `write_erase_bit` | `image_hash_exec` | +0.000 | +0.000 | +0 | +0.429 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_profile__c_profile.json` |
| `esp_idf_fault_no_abort__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_abort__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort_rollback_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc__f_profile__c_profile.json` |
| `esp_idf_fault_no_crc__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_crc__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc_copy_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_copy_guard__f_profile__c_profile.json` |
| `esp_idf_fault_no_crc_copy_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_copy_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc_copy_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_copy_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_crc_copy_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_copy_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc_crc_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_crc_guard__f_profile__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_crc_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_fallback__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback__f_profile__c_profile.json` |
| `esp_idf_fault_no_fallback__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_fallback__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_fallback__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_profile__c_profile.json` |
| `esp_idf_fault_single_sector__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_single_sector__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_profile__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_profile__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_crc_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_no_rollback__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_profile__c_profile.json` |
| `esp_idf_ota_no_rollback__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_no_rollback__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_no_rollback__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_rollback__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_profile__c_profile.json` |
| `esp_idf_ota_rollback__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_rollback__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_rollback__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_rollback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback_guard__f_profile__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_rollback_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_rollback_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_ss_guard__f_profile__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_profile__c_profile.json` |
| `esp_idf_ota_ss_guard__f_profile__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_ss_guard__f_write_erase_bit__c_profile` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_ss_guard__f_write_erase_bit__c_image_hash_exec` | ok | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_profile.json` |
| `esp_idf_ota_upgrade__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec.json` |
