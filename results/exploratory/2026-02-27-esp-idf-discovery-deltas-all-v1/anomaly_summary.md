# Exploratory Matrix Summary

- Generated: `2026-02-28T040818Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1`
- Cases planned: `44`
- Cases with report: `44`
- Cases missing report: `0`
- Control mismatches: `4`
- Anomalous fault points: `16`
- OtaData drift points (all): `142`
- OtaData benign transitions: `117`
- OtaData allowlisted points: `117`
- OtaData suspicious drift points: `25`

## Top Clusters

| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 12.876 | control_mismatch | `{"actual_control_outcome": "no_boot", "expected_control_outcome": "success"}` | 4 | 4 | 2 |
| 2 | 6.592 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "early"}` | 2 | 2 | 1 |
| 3 | 6.592 | fault_anomaly | `{"fault_type": "w", "outcome": "no_boot", "phase": "mid"}` | 2 | 2 | 1 |
| 4 | 4.394 | fault_anomaly | `{"fault_type": "w", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 5 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 6 | 4.394 | fault_anomaly | `{"fault_type": "e", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 7 | 4.394 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "early"}` | 2 | 2 | 1 |
| 8 | 4.394 | fault_anomaly | `{"fault_type": "b", "outcome": "wrong_image", "phase": "mid"}` | 2 | 2 | 1 |
| 9 | 3.219 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "w", "phase": "late"}` | 4 | 4 | 1 |
| 10 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "late"}` | 4 | 4 | 1 |
| 11 | 3.219 | otadata_drift | `{"drift_class": "suspicious_crc", "fault_type": "b", "phase": "late"}` | 4 | 4 | 1 |
| 12 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "w", "phase": "early"}` | 4 | 4 | 1 |
| 13 | 3.219 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "e", "phase": "single"}` | 4 | 4 | 1 |
| 14 | 2.079 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "early"}` | 1 | 1 | 1 |
| 15 | 2.079 | fault_anomaly | `{"fault_type": "b", "outcome": "no_boot", "phase": "mid"}` | 1 | 1 | 1 |
| 16 | 1.648 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "w", "phase": "mid"}` | 2 | 2 | 1 |
| 17 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "b", "phase": "early"}` | 1 | 1 | 1 |
| 18 | 0.520 | otadata_drift | `{"drift_class": "suspicious_failure", "fault_type": "b", "phase": "mid"}` | 1 | 1 | 1 |
| 19 | 0.347 | otadata_drift | `{"drift_class": "suspicious_seq", "fault_type": "b", "phase": "early"}` | 1 | 1 | 1 |

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 7.514 | `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_profile` | `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | `crc_guard` | `write_erase_bit` | `profile` | +0.429 | +0.429 | +1 | +0.714 |
| 2 | 6.475 | `esp_idf_fault_no_crc_crc_guard__f_profile__c_profile` | `esp_idf_ota_crc_guard__f_profile__c_profile` | `crc_guard` | `profile` | `profile` | +0.250 | +0.250 | +1 | +0.750 |
| 3 | 5.100 | `esp_idf_fault_no_abort__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.200 | +0.200 | +1 | +0.000 |
| 4 | 4.725 | `esp_idf_fault_no_abort__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.125 | +0.125 | +1 | +0.000 |
| 5 | 2.167 | `esp_idf_fault_no_crc__f_profile__c_profile` | `esp_idf_ota_upgrade__f_profile__c_profile` | `upgrade` | `profile` | `profile` | +0.556 | +0.000 | +0 | +0.000 |
| 6 | 2.167 | `esp_idf_fault_no_crc__f_write_erase_bit__c_profile` | `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | `upgrade` | `write_erase_bit` | `profile` | +0.556 | +0.000 | +0 | +0.000 |
| 7 | 0.000 | `esp_idf_fault_no_crc_crc_guard__f_profile__c_image_hash_exec` | `esp_idf_ota_crc_guard__f_profile__c_image_hash_exec` | `crc_guard` | `profile` | `image_hash_exec` | +0.000 | +0.000 | +0 | +0.500 |
| 8 | 0.000 | `esp_idf_fault_no_crc_crc_guard__f_write_erase_bit__c_image_hash_exec` | `esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec` | `crc_guard` | `write_erase_bit` | `image_hash_exec` | +0.000 | +0.000 | +0 | +0.429 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_crc_covers_state__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_crc_covers_state__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_profile__c_profile.json` |
| `esp_idf_fault_no_abort__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_profile__c_image_hash_exec.json` |
| `esp_idf_fault_no_abort__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_write_erase_bit__c_profile.json` |
| `esp_idf_fault_no_abort__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_fault_no_abort__f_write_erase_bit__c_image_hash_exec.json` |
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
| `esp_idf_ota_crc_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_profile.json` |
| `esp_idf_ota_crc_guard__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_crc_guard__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_no_rollback__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_profile__c_profile.json` |
| `esp_idf_ota_no_rollback__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_no_rollback__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_no_rollback__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_no_rollback__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_rollback__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_profile__c_profile.json` |
| `esp_idf_ota_rollback__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_rollback__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_rollback__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_rollback__f_write_erase_bit__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_profile.json` |
| `esp_idf_ota_upgrade__f_profile__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_profile__c_image_hash_exec.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_profile.json` |
| `esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/reports/esp_idf_ota_upgrade__f_write_erase_bit__c_image_hash_exec.json` |
