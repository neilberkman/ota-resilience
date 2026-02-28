# Exploratory Matrix Summary

- Generated: `2026-02-28T070033Z`
- Output dir: `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-fallback-guard-matrix`
- Cases planned: `2`
- Cases with report: `2`
- Cases missing report: `0`
- Control mismatches: `0`
- Anomalous fault points: `0`
- OtaData drift points (all): `8`
- OtaData benign transitions: `8`
- OtaData allowlisted points: `8`
- OtaData allowlist lanes: `1`
- OtaData suspicious drift points: `0`

## Top Clusters

No anomalies detected.

## Baseline vs Defect Deltas

| Rank | Score | Defect | Baseline | Scenario | Fault | Criteria | Δfailure | Δbrick | Δcontrol | Δotadata(susp) |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 1 | 4.000 | `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile` | `esp_idf_ota_fallback_guard__f_profile__c_profile` | `fallback_guard` | `profile` | `profile` | +0.000 | +0.000 | +0 | +0.000 |

## Run Records

| Case | Status | Exit | Report |
| --- | --- | ---: | --- |
| `esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-fallback-guard-matrix/reports/esp_idf_fault_no_fallback_fallback_guard__f_profile__c_profile.json` |
| `esp_idf_ota_fallback_guard__f_profile__c_profile` | reused | 0 | `/Users/neil/mirala/ota-resilience/results/exploratory/2026-02-28-esp-idf-fallback-guard-matrix/reports/esp_idf_ota_fallback_guard__f_profile__c_profile.json` |
