# Exploratory Matrix Summary

- Generated: `2026-03-01T034824Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1`
- Cases planned: `76`
- Cases with report: `76`
- Cases missing report: `0`
- Control mismatches: `10`
- Anomalous fault points: `57`
- OtaData drift points (all): `272`
- OtaData benign transitions: `50`
- OtaData allowlisted points: `50`
- OtaData allowlist lanes: `32`
- OtaData allowlist eligible lanes: `4`
- OtaData allowlist ineligible lanes: `28`
- OtaData allowlist min samples (fault/success): `8/4`
- OtaData suspicious drift points: `222`

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
| 11 | 5.838 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "w", "phase": "late"}` | 48 | 48 | 16 |
| 12 | 5.748 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "w", "phase": "early"}` | 22 | 22 | 6 |
| 13 | 5.748 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "single"}` | 22 | 22 | 6 |
| 14 | 5.723 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "w", "phase": "mid"}` | 30 | 30 | 9 |
| 15 | 5.375 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "early"}` | 5 | 5 | 5 |
| 16 | 5.375 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "mid"}` | 5 | 5 | 5 |
| 17 | 4.394 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 18 | 4.394 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 19 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 20 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 21 | 4.394 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 22 | 4.159 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "mid"}` | 3 | 3 | 2 |
| 23 | 3.996 | otadata_drift | `{"drift_class": "suspicious_active_entry", "fault_type": "w", "phase": "early"}` | 10 | 10 | 3 |
| 24 | 3.996 | otadata_drift | `{"drift_class": "suspicious_active_entry", "fault_type": "e", "phase": "single"}` | 10 | 10 | 3 |
| 25 | 3.296 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "late"}` | 2 | 2 | 2 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δcontrol_outcome | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 13.700 | `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_ss_guard__f_write_erase_bit__c_profile` | `ss_guard` | `write_erase_bit` | `profile` | +1.000 | +1.000 | +1 | +2 | +0.000 |
| 2 | 13.400 | `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | `esp_idf_ota_ss_guard__f_profile__c_profile` | `ss_guard` | `profile` | `profile` | +1.000 | +1.000 | +1 | +2 | +0.000 |
| 3 | 10.443 | `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | `crc_guard` | `write_erase_bit` | `profile` | +0.429 | +0.429 | +1 | +2 | +0.000 |
| 4 | 9.350 | `esp_idf_fault_no_crc_crc_guard__f_profile__c_profile` | `esp_idf_ota_crc_guard__f_profile__c_profile` | `crc_guard` | `profile` | `profile` | +0.250 | +0.250 | +1 | +2 | +0.000 |
| 5 | 9.100 | `esp_idf_fault_no_abort__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.200 | +0.200 | +1 | +2 | -0.333 |
| 6 | 8.725 | `esp_idf_fault_no_abort__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.125 | +0.125 | +1 | +2 | +0.000 |
| 7 | 7.100 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_profile` | `esp_idf_ota_rollback_guard__f_profile__c_profile` | `rollback_guard` | `profile` | `profile` | +1.000 | +0.800 | +0 | +1 | -1.000 |
| 8 | 7.039 | `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_rollback_guard__f_write_erase_bit__c_profile` | `rollback_guard` | `write_erase_bit` | `profile` | +0.857 | +0.875 | +0 | +1 | -1.000 |
| 9 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | `crc_schema_guard` | `profile` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 10 | 6.000 | `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile` | `crc_schema_guard` | `write_erase_bit` | `profile` | +0.000 | +0.000 | +1 | +1 | +0.000 |
| 11 | 4.000 | `esp_idf_fault_no_abort_rollback_guard__f_profile__c_image_hash_exec` | `esp_idf_ota_rollback_guard__f_profile__c_image_hash_exec` | `rollback_guard` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +1 | +0 | -1.000 |
| 12 | 4.000 | `esp_idf_fault_no_abort_rollback_guard__f_write_erase_bit__c_image_hash_exec` | `esp_idf_ota_rollback_guard__f_write_erase_bit__c_image_hash_exec` | `rollback_guard` | `write_erase_bit` | `image_hash_exec` | +0.000 | +0.000 | +1 | +0 | -1.000 |
| 13 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile` | `esp_idf_ota_fallback_guard__f_profile__c_profile` | `fallback_guard` | `profile` | `profile` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 14 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_image_hash_exec` | `esp_idf_ota_fallback_guard__f_profile__c_image_hash_exec` | `fallback_guard` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 15 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_fallback_guard__f_write_erase_bit__c_profile` | `fallback_guard` | `write_erase_bit` | `profile` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 16 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_image_hash_exec` | `esp_idf_ota_fallback_guard__f_write_erase_bit__c_image_hash_exec` | `fallback_guard` | `write_erase_bit` | `image_hash_exec` | +0.000 | +0.000 | +0 | +2 | +0.000 |
| 17 | 2.167 | `esp_idf_fault_no_crc__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.556 | +0.000 | +0 | +0 | +0.000 |
| 18 | 2.167 | `esp_idf_fault_no_crc__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.556 | +0.000 | +0 | +0 | +0.000 |
| 19 | 0.000 | `esp_idf_fault_single_sector__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.000 | +0.000 | +0 | +0 | +0.667 |
| 20 | 0.000 | `esp_idf_fault_single_sector__f_profile__c_image_hash_exec` | `esp_idf_ota_upgrade__f_profile__c_image_hash_exec` | `upgrade` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +0 | +0 | +0.667 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state_crc_schema_guard__f_write_erase_bit__c_image_hash_exec.json` |
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
| `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback_fallback_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_fallback_fallback_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_profile__c_profile.json` |
| `esp_idf_fault_single_sector__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_single_sector__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector_ss_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_profile__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_single_sector_ss_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_crc_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_schema_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_fallback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_fallback_guard__f_profile__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_fallback_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_fallback_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_fallback_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_fallback_guard__f_write_erase_bit__c_image_hash_exec.json` |
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
| `esp_idf_ota_ss_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_profile__c_profile.json` |
| `esp_idf_ota_ss_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_ss_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_ss_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_ss_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_profile.json` |
| `esp_idf_ota_upgrade__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec.json` |
