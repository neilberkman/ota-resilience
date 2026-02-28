# OTA Resilience — Agent Handoff Document

## What This Project Is

A Renode-based fault injection testbed for OTA firmware updates. It simulates power loss (and other faults) at every NVM write/erase point during a bootloader's update process, then checks if the device can still boot. If it can't boot after the fault, that's a "brick" — a real-world vulnerability.

**Public repo**: `git@github.com:neilberkman/ota-resilience.git`

**CARDINAL RULE**: This is a **clean room public repo**. ZERO proprietary info. No company names, no internal peripheral names, no private firmware paths. EVER. See MEMORY.md for the nuclear lesson about IP contamination.

## Architecture Overview

```
profiles/*.yaml          -- Declarative bootloader profiles (self-test + exploratory lanes)
    |
    v
scripts/profile_loader.py  -- Parses YAML, generates robot variables
    |
    v
scripts/audit_bootloader.py  -- Orchestrator: calibration → sweep → summary
    |
    v
tests/ota_fault_point.robot  -- Robot Framework test suite (Renode bridge)
    |
    v
scripts/run_runtime_fault_sweep.resc  -- Renode script: fault injection + boot outcome eval
    |
    v
peripherals/NRF52NVMC.cs  -- Custom Renode peripheral: word-level write/erase tracking
```

### How a Run Works

1. **Profile** defines: platform, bootloader ELF, slot layout, images, pre-boot state, success criteria, fault types
2. **Calibration**: Boot once without faults, count total NVM writes and erases
3. **Sweep**: For each fault point N (0..max_writes):
   - Load images + pre-boot state
   - Arm fault at write N (or erase N, or bit-corrupt write N)
   - Reset CPU, run until fault fires or timeout
   - Take flash snapshot at exact fault moment
   - Reset CPU again (power cycle simulation), boot from faulted flash
   - Evaluate: did it boot to a valid slot? → success or brick
4. **Summary**: brick count, brick rate, categorized failures, verdict

### Two Platform Paths

| Platform        | File                        | Speed                             | Used By                                       |
| --------------- | --------------------------- | --------------------------------- | --------------------------------------------- |
| NVMemory (slow) | `cortex_m0_nvm.repl`        | Per-write tracking natively       | naive_copy, fault_variants, resilient, nxboot |
| NVMC (fast)     | `cortex_m4_flash_fast.repl` | Word-level diff on CONFIG WEN→REN | MCUboot, ESP-IDF, riotboot                    |

The fast path (`NRF52NVMC.cs`) diffs the entire flash on each NVMC CONFIG transition to count individual changed words. This is what enables write-level fault injection for real bootloaders that use nRF52 NVMC registers.

### Key Optimizations

- **Trace replay**: During calibration, records every `(writeIndex, flashOffset, value)`. During sweep, reconstructs flash state from trace (~20ms Python) instead of re-emulating Phase 1 (~seconds). Only Phase 2 recovery boot needs emulation. 10-100x speedup.
- **Write-address heuristic**: Classifies writes into tiers (trailer=exhaustive, boundary=dense, bulk=sparse). 10x reduction in fault points for MCUboot.
- **Parallel workers**: `--workers N` splits fault points across N Renode instances.
- **Phase 2 brick timeout**: Detects bricked devices in ~0.1s (zero writes = dead) instead of 120s default.

## Current State

### Branch: `main` (active branch)

- Main has the exploratory matrix stack through lane-scoped OtaData allowlisting, OtaData success-criteria assertions (with scope control), new runtime fault types (`write_rejection`, `reset_at_time`), extended ESP guard profile pairs (including `no_fallback` fallback-guard), and control-outcome-aware defect scoring.
- Working tree state should be checked with `git status --short --branch` before resuming long runs.
- Local MCUboot workspace (`third_party/zephyr_ws/bootloader/mcuboot`): branch `fix/revert-copy-done-any`, local commit `b05be3a5`
- Bit-corruption fault mode is committed (not pending)

**Self-test baseline: 45/45 passing** (latest full validation status before adding exploratory skip-self-test profiles)

### What's Been Proven

Three real MCUboot CVE-class bugs detected via differential testing:

1. **PR #2100** (swap-move revert magic): Broken 9.7% bricks → Fixed 0%. ELFs at `results/oss_validation/assets/oss_mcuboot_pr2100_*.elf`
2. **PR #2109** (swap-scratch header reload): Broken 33.3% bricks → Fixed 0%. Requires different-sized images. ELFs at `results/oss_validation/assets/oss_mcuboot_pr2109_*.elf`
3. **PR #2199** (stuck revert): Broken 100% wrong_image → Fixed 0%.

Additional exploratory real-binary runs were completed for geometry/math bug PRs:

4. **PR #2205, #2206, #2214**: built and quick-audited as broken/fixed pairs on nRF52840 geometry.
   - No differential found in quick sweeps (all pairs PASS with 0 failures).
   - Reports: `results/oss_validation/reports/2026-02-26-pr2205-2206-2214/*.quick.json`
   - Important: these bug classes are geometry-sensitive and may require non-nRF52840 sector/topology conditions to trigger.

5. **Geometry-trigger follow-up (2026-02-26)**:
   - Added forced-trailer scratch variants for PR2206 (`CONFIG_BOOT_MAX_IMG_SECTORS=1024`), plus fuller staging images.
   - PR2206 geometry quick runs now hit much larger write-space (broken: 32,441 writes / 88 erases; fixed: 14,554 / 36), proving the trigger changes execution.
   - Two payload probes (`img_size=0x69000` and `0x66000`) still fail control boot with `no_boot` for both revisions, so no clean differential yet.
   - PR2214 fuller offset image still calibrates as `0 writes / 118 erases` on this target and remains non-differential.
   - Reports: `results/oss_validation/reports/2026-02-26-geometry/*.quick.json`

6. **PR2206 non-geometry threshold sweep (2026-02-27)**:
   - Added `scripts/sweep_pr2206_geometry_threshold.py` to automatically size-sweep staging images, find fixed control-boot threshold, and compare broken vs fixed around the boundary.
   - Fixed threshold on this target: `0x9000` payload boots; `0xA000` payload does not boot.
   - Broken and fixed match at all comparison points (`0x8000`, `0x9000`, `0xA000`) → no differential found in this geometry either.
   - Reports: `results/oss_validation/reports/2026-02-27-pr2206-nongeom-threshold-v2.json` and per-run JSONs in `results/oss_validation/reports/2026-02-27-pr2206-nongeom-threshold-v2/`

7. **PR2206 forced-trailer geometry threshold sweep (2026-02-27)**:
   - Ran the same threshold sweep against `oss_mcuboot_pr2206_scratch_geom_{broken,fixed}.elf`.
   - No fixed-success point was found in the tested window (`0x3000..0x30000`): outcomes were `wrong_image` at smaller payloads and `no_boot` at larger payloads.
   - Broken and fixed still match at candidate comparison points (`0x5000`, `0x30000`) → no differential found.
   - Reports: `results/oss_validation/reports/2026-02-27-pr2206-geom-threshold-v2.json` and per-run JSONs in `results/oss_validation/reports/2026-02-27-pr2206-geom-threshold-v2/`

8. **ESP-IDF defect profile refresh (2026-02-27)**:
   - Updated defect profiles to avoid stateless runs: enabled copy-on-boot trigger for `no_abort` and `no_fallback`, fixed defect-specific CRC seeds for `crc_covers_state`, and adjusted `single_sector` rollback seed layout.
   - Post-patch quick calibrations:
     - `esp_idf_fault_no_abort`: `2049 writes / 2 erases`
     - `esp_idf_fault_no_fallback`: `2052 writes / 3 erases`
     - `esp_idf_fault_crc_covers_state`: `2052 writes / 3 erases`
     - `esp_idf_fault_single_sector`: `3 writes / 1 erase`
   - Matching baseline quick runs:
     - `esp_idf_ota_upgrade`: `2052 writes / 3 erases`
     - `esp_idf_ota_rollback`: `3 writes / 1 erase`
   - Quick runs are still non-differential (0 bricks across baseline and defect profiles), but stateless/no-op calibrations were removed for key defect variants.
   - Deep sweeps (full heuristic sets, 4 workers) are also currently non-differential:
     - `esp_idf_ota_upgrade`: `0/365` bricks
     - `esp_idf_fault_no_fallback`: `0/365` bricks
     - `esp_idf_fault_crc_covers_state`: `0/365` bricks
     - `esp_idf_fault_no_abort`: `0/359` bricks
   - `esp_idf_fault_no_crc` full run (includes bit-corruption points) is high-signal: `719/727` wrong-image failures (`brick_rate ≈ 98.9%`).
   - Matching bounded baseline rerun completed (`esp_idf_ota_upgrade_hash_bit_bounded.full.json`, `image_hash + bit_corruption`, `max_step_limit=0x180000`): also `719/727` wrong-image failures (`brick_rate ≈ 98.9%`).
   - Conclusion: `no_crc` vs baseline is currently non-differential under this configuration; both share the same high wrong-image failure signature.
   - Deep reports: `results/oss_validation/reports/2026-02-27-esp-idf-deep/*.full.json`
   - Reports: `results/oss_validation/reports/2026-02-27-esp-idf-refresh/*.quick.json`

9. **ESP-IDF model tuning follow-up (2026-02-27, later batch)**:
   - Added `success_criteria.image_hash_slot` plumbing end-to-end (`profile_loader.py` → Robot vars → `run_runtime_fault_sweep.resc`) so hash checks can be gated to a specific boot slot (used as `exec` for copy-path checks).
   - Normalized profile image digests to slot data length (truncate/pad with `0xFF`) so profile-side SHA-256 matches runtime exec-slot hashing.
   - Fixed synthetic ESP slot firmware masking: `gen_esp_idf_images.py` no longer rewrites `VTOR` inside app code, so observed `boot_slot` reflects bootloader choice.
   - Relaxed ESP model vector validation to accept reset vectors in either OTA slot, which avoids copy-path false fallback caused by slot-address-coupled vectors.
   - Exploratory copy-guard pair (`esp_idf_ota_upgrade_copy_guard` vs `esp_idf_fault_no_crc_copy_guard`) remains non-differential even with deep bounded sweep: both `0/727` bricks, control `boot_slot=exec`.
   - New CRC-guard pair now provides a concrete `no_crc` differential:
     - Baseline `esp_idf_ota_crc_guard`: `0/4` bricks, control `success/exec` (PASS)
     - Defect `esp_idf_fault_no_crc_crc_guard`: `1/4` bricks (`no_boot`), control `no_boot/staging` (PASS because issues expected)
   - Reports:
     - `results/oss_validation/reports/2026-02-27-esp-idf-copy-guard/*.json`
     - `results/oss_validation/reports/2026-02-27-esp-idf-crc-guard/*.json`

10. **Exploratory discovery matrix runner (2026-02-27, later batch)**:
   - Added `scripts/run_exploratory_matrix.py` for discovery-first campaigns:
     - Expands profile matrices from baseline scenarios (and optionally defect profiles)
     - Applies generic fault/criteria presets (`profile`, `write_erase`, `write_erase_bit` and `profile`, `vtor_any`, `image_hash_exec`)
     - Executes `audit_bootloader.py` per case
     - Clusters anomalies (`control_mismatch` + fault anomalies) with reproducibility/novelty scoring
     - Emits `matrix_results.json` + `anomaly_summary.md`
   - First runs:
     - Baseline-only matrix (`16` cases): `0` clusters
     - Defect-inclusive matrix (`24` capped cases): `11` clusters, `4` control mismatches, `16` anomalous points
   - Artifacts:
     - `results/exploratory/2026-02-27-esp-idf-discovery-v1/`
     - `results/exploratory/2026-02-27-esp-idf-discovery-with-defects-v1/`

11. **Exploratory matrix analyzer v2 (2026-02-27, latest batch)**:
   - Upgraded `scripts/run_exploratory_matrix.py` to:
     - Use coarser cluster signatures (drop over-specific `boot_slot` / `image_hash_match` keys from primary cluster identity).
     - Emit per-case metrics (`case_metrics`) including failure/brick/wrong-image rates.
     - Rank baseline-vs-defect regressions (`defect_deltas`) by delta score.
     - Classify OtaData drift as `benign_state_transition` vs `suspicious_*` and score defect deltas using suspicious drift only.
     - Down-weight OtaData-only clusters in anomaly ranking so control mismatches and boot-outcome anomalies surface first.
     - Detect and cluster `otadata_drift` anomalies from runtime signals.
   - Upgraded `scripts/run_runtime_fault_sweep.resc` to emit post-boot OtaData signals:
     - entry0/entry1 seq/state/crc words
     - decoded state names
     - active-entry guess and compact `otadata_digest`
   - Fresh matrix run (16 cases, baseline+no_crc pairs) now reports:
     - `8` clusters (including OtaData drift clusters)
     - `8` defect delta comparisons, with `2` ranked regressions (`no_crc` vs baseline in `criteria=profile`)
   - Expanded full ESP matrix run (44 cases, baseline + all defect profiles) now reports:
     - `24` clusters, `24` defect delta comparisons, `4` control mismatches
     - Top regressions include:
       - `no_crc_crc_guard` vs `ota_crc_guard` (`Δcontrol=+1`, `Δbrick up to +0.428571`)
       - `no_abort` vs `ota_upgrade` (`Δcontrol=+1`, `Δbrick up to +0.2`)
       - `no_crc` vs `ota_upgrade` (`Δfailure=+0.555556`, wrong-image class)
   - Artifacts:
     - `results/exploratory/2026-02-27-esp-idf-discovery-deltas-v2/`
     - `results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/`

12. **Exploratory matrix analyzer v3 allowlist pass (2026-02-28, latest batch)**:
   - Added scenario-aware OtaData allowlisting in `scripts/run_exploratory_matrix.py`:
     - Builds an allowlist from baseline runs whose control outcome matches expectations.
     - Converts scenario-allowlisted `suspicious_*` classes to `benign_allowlisted`.
     - Tracks both normalized and raw drift class counts per case.
     - Emits `otadata_allowlist` plus totals (`otadata_allowlisted_points_total`, `otadata_allowlist_scenarios`) in `matrix_results.json`.
   - Reused existing reports (`--reuse-existing`) to regenerate matrix artifacts with new clustering/scoring:
     - Focused lane (`16` cases): `5` clusters, `46` allowlisted points, `0` suspicious OtaData drift points.
     - Full lane (`44` cases): `19` clusters (down from `24`), `117` allowlisted points, `25` suspicious OtaData drift points, `4` control mismatches.
   - Result: OtaData noise is still visible for auditability but no longer dominates top exploratory clusters in scenarios where baseline already shows that drift pattern.
   - Artifacts refreshed:
     - `results/exploratory/2026-02-27-esp-idf-discovery-deltas-v2/`
     - `results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/`

13. **OtaData success-criteria assertions + rollback guard pair (2026-02-28, latest batch)**:
   - Added `success_criteria.otadata_expect` end-to-end:
     - `scripts/profile_loader.py` parses/normalizes OtaData expectations and emits `SUCCESS_OTADATA_EXPECT`.
     - `tests/ota_fault_point.robot` forwards `SUCCESS_OTADATA_EXPECT` into Renode.
     - `scripts/run_runtime_fault_sweep.resc` validates expected OtaData signals and exposes:
       - `otadata_expect_ok`
       - `otadata_expect_mismatches`
     - OtaData expectation failures now classify as `wrong_image` when VTOR/PC checks pass.
   - Added rollback guard exploratory pair:
     - `profiles/esp_idf_ota_rollback_guard.yaml`
     - `profiles/esp_idf_fault_no_abort_rollback_guard.yaml`
   - Quick differential confirmation:
     - Baseline guard: `0/4` bricks, control `success/exec`
     - Defect guard: `5/5` bricks, control `wrong_image/exec` (OtaData mismatch: `PENDING_VERIFY` vs expected `ABORTED|UNDEFINED`)
     - Reports: `results/oss_validation/reports/2026-02-28-esp-idf-rollback-guard/*.quick.json`
   - Focused matrix confirmation (2-case lane):
     - `5` clusters, `1` defect delta, top delta score `5.1`
     - Artifact: `results/exploratory/2026-02-28-esp-idf-rollback-guard-matrix-v2/`
   - Initial full ESP matrix refresh with new guard profiles included:
     - `52` cases, `25` clusters, `6` control mismatches, `28` defect deltas
     - `otadata_allowlist_scenarios=5`, `otadata_allowlist_lanes=20`, `otadata_allowlisted_points_total=138`
     - Artifact: `results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/`
   - Tightened allowlist scope in `run_exploratory_matrix.py`:
     - OtaData allowlists are now keyed by `scenario + fault_preset + criteria_preset` lane (not scenario-wide only).
     - Prevents cross-lane baseline drift from over-normalizing suspicious classes in unrelated lanes.

14. **New runtime fault types + OtaData scope control (2026-02-28, latest batch)**:
   - Implemented and wired end-to-end:
     - `write_rejection` (`fault_type='r'`, `WriteFaultMode=3`) — rejects the target write, leaving pre-write word intact.
     - `reset_at_time` (`fault_type='t'`) — deterministic time-based reset during phase-1 execution, then recovery boot.
   - Added `success_criteria.otadata_expect_scope` (`always` or `control`):
     - Parsed in `scripts/profile_loader.py`, passed through Robot vars, enforced in `scripts/run_runtime_fault_sweep.resc`.
     - `control` scope enforces OtaData assertions only on control boots, avoiding false positives on injected-fault points.
   - Quick smoke reports:
     - `esp_idf_ota_upgrade_write_rejection`: `0/3` bricks, control `success/exec` (PASS)
     - `esp_idf_ota_upgrade_reset_at_time`: `0/3` bricks, control `success/exec` (PASS)
   - Higher-sample non-quick sweeps (4 workers, heuristic 362 points each):
     - `esp_idf_ota_upgrade_write_rejection`: `0/362` bricks, control `success/exec` (PASS)
     - `esp_idf_ota_upgrade_reset_at_time`: `0/362` bricks, control `success/exec` (PASS)
   - Focused preset smoke matrix (`write_reject` + `time_reset`) remains clean:
     - `2` cases, `0` clusters, `0` control mismatches.
   - Artifacts:
     - `results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types/*.quick.json`
     - `results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types-full/*.full.json`
     - `results/exploratory/2026-02-28-esp-idf-faulttype-preset-smoke/`

15. **Extended guard pairs + matrix refresh (2026-02-28, latest batch)**:
   - Added exploratory baseline/defect guard pairs:
     - `esp_idf_ota_ss_guard` vs `esp_idf_fault_single_sector_ss_guard`
     - `esp_idf_ota_crc_schema_guard` vs `esp_idf_fault_crc_covers_state_crc_schema_guard`
   - Quick differential outcomes:
     - `ss_guard`: baseline `0/4` bricks (`success/staging`) vs defect `4/4` bricks (`no_boot/exec`).
     - `crc_schema_guard`: baseline control `success/exec` with `3/6` brick faults; defect control `wrong_image/exec` with `3/6` brick faults (control mismatch differential).
   - Focused guard matrix:
     - `4` cases, `12` clusters, `2` control mismatches, `2` defect deltas.
     - Artifact: `results/exploratory/2026-02-28-esp-idf-extended-guards-matrix/`
   - Full ESP matrix refresh (`--reuse-existing`) with expanded default profile set:
     - `68` cases, `32` clusters, `10` control mismatches, `36` defect deltas.
     - `otadata_allowlist_scenarios=7`, `otadata_allowlist_lanes=28`, `otadata_allowlisted_points_total=191`.
     - Artifact refreshed: `results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/`

16. **No-fallback guard pair + control-outcome delta scoring (2026-02-28, latest batch)**:
   - Added fallback-guard exploratory pair:
     - `profiles/esp_idf_ota_fallback_guard.yaml`
     - `profiles/esp_idf_fault_no_fallback_fallback_guard.yaml`
   - Scenario: OtaData selects slot1, but slot1 vector table is intentionally invalid.
     - Baseline should fallback to slot0 (`success/exec`).
     - `no_fallback` defect bricks in control (`no_boot`) instead of falling back.
   - Quick pair confirmation:
     - Baseline fallback-guard: `0/4` bricks, control `success/exec` (PASS)
     - Defect fallback-guard: `0/4` bricks, control `no_boot` (PASS with expected control outcome)
     - Reports: `results/oss_validation/reports/2026-02-28-esp-idf-fallback-guard/*.quick.json`
   - Focused fallback matrix:
     - `2` cases, `1` defect delta.
     - Artifact: `results/exploratory/2026-02-28-esp-idf-fallback-guard-matrix/`
   - Upgraded `scripts/run_exploratory_matrix.py` defect scoring:
     - Added baseline-vs-defect control-outcome comparison (`control_outcome_changed`, `control_outcome_shift`) into `defect_deltas`.
     - This captures regressions even when both profiles satisfy their own expected control outcomes.
   - Full ESP matrix refresh after fallback profiles + scoring update:
     - `76` cases, `32` clusters, `10` control mismatches, `40` defect deltas.
     - `otadata_allowlist_scenarios=8`, `otadata_allowlist_lanes=32`, `otadata_allowlisted_points_total=235`.
     - Artifact refreshed: `results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1/`

### Bootloader Coverage

| Bootloader            | Type                     | Profiles                                                         | Notes                                          |
| --------------------- | ------------------------ | ---------------------------------------------------------------- | ---------------------------------------------- |
| Custom A/B resilient  | Toy model                | 3 (resilient_none, resilient_meta_faults, resilient_multi_fault) | Built-in reference implementation              |
| Custom fault variants | Toy model, injected bugs | 8 (fault_no_crc, fault_no_fallback, etc.)                        | Each has a specific defect                     |
| Custom naive copy     | Toy model, worst case    | 3 (bare, small_image, with_marker)                               | 100% brick rate                                |
| NuttX nxboot          | Model                    | 4 (none, rollback, header_validation, no_recovery)               | Clean-room model of nxboot algorithm           |
| RIOT riotboot         | Model                    | 1 (riotboot_standalone)                                          | VID/FW version selection                       |
| MCUboot swap-move     | REAL BINARY              | Multiple profiles                                                | Built from Zephyr+MCUboot, real swap algorithm |
| MCUboot swap-scratch  | REAL BINARY              | Multiple profiles                                                | Includes PR2109 and exploratory PR2205/2206    |
| MCUboot swap-offset   | REAL BINARY              | Multiple profiles                                                | Includes upstream head and exploratory PR2214   |
| ESP-IDF OTA           | Model                    | 22 (11 baseline + 11 defect-focused variants)                    | Clean-room otadata + copy-on-boot stress path  |

## Files You Need to Know

### Core Pipeline

| File                                   | What It Does                                                                                                      |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `scripts/audit_bootloader.py`          | **Main orchestrator.** `--profile foo.yaml --output result.json`. Calibration, sweep, summary, verdict.           |
| `scripts/profile_loader.py`            | YAML profile parser + validator. Generates robot variables.                                                       |
| `scripts/run_runtime_fault_sweep.resc` | **The Renode script.** All fault injection logic lives here. Python embedded in Renode's IronPython. ~1100 lines. |
| `peripherals/NRF52NVMC.cs`             | Custom C# peripheral for word-level write tracking + fault injection. The core innovation.                        |
| `tests/ota_fault_point.robot`          | Robot Framework bridge between Python orchestrator and Renode.                                                    |
| `scripts/self_test.py`                 | Runs all 45 profiles, checks verdicts. `--quick` for fast subset.                                                 |

### Supporting Scripts

| File                               | What It Does                                                            |
| ---------------------------------- | ----------------------------------------------------------------------- |
| `scripts/write_trace_heuristic.py` | Classifies writes into tiers for smart fault point selection            |
| `scripts/state_fuzzer.py`          | Opt-in deep analysis for A/B metadata (only used by resilient profiles) |
| `scripts/invariants.py`            | Metadata invariant checks for state fuzzer                              |
| `scripts/mcuboot_state_fuzzer.py`  | MCUboot-specific state fuzzer (not widely used)                         |
| `scripts/bootstrap_mcuboot_geometry_assets.sh` | Rebuild geometry-trigger MCUboot assets (PR2206 forced trailer + large images) |
| `scripts/sweep_pr2206_geometry_threshold.py` | Control-only payload-size sweep for PR2206 threshold and broken/fixed comparison |
| `scripts/run_exploratory_matrix.py` | Discovery-first matrix runner + anomaly clustering report generator |
| `scripts/run_oss_validation.py`    | MCUboot build + validate pipeline                                       |
| `scripts/geometry_matrix.py`       | MCUboot swap geometry analysis                                          |

### Bootloader Source

| Directory                       | What                                                                       |
| ------------------------------- | -------------------------------------------------------------------------- |
| `examples/resilient_ota/`       | A/B bootloader with metadata replication, CRC, atomic commit               |
| `examples/vulnerable_ota/`      | Naive copy-to-exec, no safety                                              |
| `examples/fault_variants/`      | `bootloader_variants.c` with `#ifdef DEFECT_*` for 8 defect types          |
| `examples/naive_copy/`          | Minimal naive copy variants                                                |
| `examples/nxboot_style/`        | Clean-room nxboot model                                                    |
| `examples/riotboot_standalone/` | Clean-room riotboot model                                                  |
| `examples/esp_idf_ota/`         | **NEW** — Clean-room ESP-IDF OTA model with 5 `#ifdef ESP_DEFECT` variants |

### MCUboot Real Binaries

All pre-built at `results/oss_validation/assets/*.elf`. Built via `scripts/bootstrap_mcuboot_matrix_assets.sh`. Zephyr v3.7.0, nrf52840dk. Stripped of debug info.

## Fault Types

Implemented in `NRF52NVMC.cs` and dispatched via the profile's `fault_types` list:

| Profile Name             | Code  | Implemented | How It Works                                                                                                                          |
| ------------------------ | ----- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `power_loss`             | `'w'` | Yes        | Block the Nth write entirely. Flash snapshot has N-1 writes completed.                                                                |
| `bit_corruption`         | `'b'` | Yes        | NOR flash physics: partially program the Nth write. ~50% of 1→0 bit transitions complete, rest stay at 1. Deterministic via LCG PRNG. |
| `silent_write_failure`   | `'s'` | Yes        | Faulted write "succeeds" but stores deterministic all-`0xFFFFFFFF` or all-`0x00000000`.                                              |
| `write_disturb`          | `'d'` | Yes        | Target word commits; adjacent words get unintended 1→0 flips (neighbor-cell disturb).                                                |
| `wear_leveling_corruption` | `'l'` | Yes      | Target write commits, then deterministic page-local aging bit errors are injected.                                                    |
| `interrupted_erase`      | `'e'` | Yes        | Partial erase at Nth erase: first half 0xFF, second half untouched.                                                                   |
| `multi_sector_atomicity` | `'a'` | Yes        | Partial erase on target page plus neighboring-page damage (cross-sector inconsistency).                                               |
| `write_rejection`        | `'r'` | Yes        | Rejects the target write at the fault index (keeps pre-write word), then recovery boot evaluates downstream behavior.                |
| `reset_at_time`          | `'t'` | Yes        | Injects a deterministic time-based reset during phase-1 execution (not tied to write/erase boundaries), then evaluates recovery boot. |

### Bit Corruption Details (committed)

`NRF52NVMC.cs` properties:

- `WriteFaultMode`: 0 = power_loss, 1 = bit_corruption, 2 = silent_write_failure, 3 = write_rejection, 4 = write_disturb, 5 = wear_leveling_corruption
- `CorruptionSeed`: deterministic PRNG seed (0 = use TotalWordWrites)

NOR flash physics: erased = all 1s. Programming flips bits 1→0. Interrupted programming = only SOME intended 1→0 transitions complete. Implementation: `corruptedWord = oldWord & ~(bitsToFlip & prgn_mask)` where `bitsToFlip = oldWord & ~newWord`.

Bit corruption and erase faults are forced through full execute mode (not trace replay) because they depend on NVMC peripheral state at the exact fault moment.

## Running Things

### Prerequisites

- Renode: binary at `/Users/neil/.local/bin/renode`
- renode-test: `/Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test`
- Server dir (`/tmp/renode-server`) is only needed when using source-tree `renode-test` wrappers that expect `Renode.exe` in a build output directory.
- ARM toolchain: `~/tools/gcc-arm-none-eabi-8-2018-q4-major/bin/`
- Python 3.x with PyYAML

### Commands

```bash
# Self-test (all 45 profiles, ~45 min with --quick)
python3 scripts/self_test.py \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --quick

# Single profile audit
python3 scripts/audit_bootloader.py \
  --profile profiles/mcuboot_head_upgrade.yaml \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output /tmp/result.json

# With parallel workers (faster for large write counts)
python3 scripts/audit_bootloader.py \
  --profile profiles/mcuboot_pr2109_scratch_broken.yaml \
  --workers 4 \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output /tmp/result.json

# Build ESP-IDF variants
cd examples/esp_idf_ota && make clean && make all && make strip
python3 gen_esp_idf_images.py slot --index 0 --output slot0.bin
python3 gen_esp_idf_images.py slot --index 1 --output slot1.bin
cd /Users/neil/mirala/ota-resilience

# Quick differential batch for PR2205/2206/2214 exploratory profiles
mkdir -p results/oss_validation/reports/2026-02-26-pr2205-2206-2214
for p in \
  mcuboot_pr2205_scratch_broken mcuboot_pr2205_scratch_fixed \
  mcuboot_pr2206_scratch_broken mcuboot_pr2206_scratch_fixed \
  mcuboot_pr2214_offset_broken mcuboot_pr2214_offset_fixed; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-26-pr2205-2206-2214/${p}.quick.json"
done

# Rebuild geometry-trigger assets (PR2206 forced-trailer + fuller images)
scripts/bootstrap_mcuboot_geometry_assets.sh

# PR2206 threshold sweep (control-only, broken/fixed around boundary)
python3 scripts/sweep_pr2206_geometry_threshold.py \
  --repo-root /Users/neil/mirala/ota-resilience \
  --fixed-elf results/oss_validation/assets/oss_mcuboot_pr2206_scratch_fixed.elf \
  --broken-elf results/oss_validation/assets/oss_mcuboot_pr2206_scratch_broken.elf \
  --output results/oss_validation/reports/2026-02-27-pr2206-nongeom-threshold-v2.json \
  --results-dir results/oss_validation/reports/2026-02-27-pr2206-nongeom-threshold-v2 \
  --min-payload 0x5000 --max-payload 0x30000 --quantum 0x1000 \
  --max-step-limit 0x180000 --max-writes-cap 0x20000 --reuse-existing

# Same sweep against forced-trailer geometry pair
python3 scripts/sweep_pr2206_geometry_threshold.py \
  --repo-root /Users/neil/mirala/ota-resilience \
  --fixed-elf results/oss_validation/assets/oss_mcuboot_pr2206_scratch_geom_fixed.elf \
  --broken-elf results/oss_validation/assets/oss_mcuboot_pr2206_scratch_geom_broken.elf \
  --output results/oss_validation/reports/2026-02-27-pr2206-geom-threshold-v2.json \
  --results-dir results/oss_validation/reports/2026-02-27-pr2206-geom-threshold-v2 \
  --min-payload 0x5000 --max-payload 0x30000 --quantum 0x1000 \
  --floor-payload 0x3000 \
  --max-step-limit 0x180000 --max-writes-cap 0x20000 --reuse-existing

# ESP-IDF defect profile refresh quick batch
mkdir -p results/oss_validation/reports/2026-02-27-esp-idf-refresh
for p in \
  esp_idf_fault_no_abort \
  esp_idf_fault_no_fallback \
  esp_idf_fault_crc_covers_state \
  esp_idf_fault_single_sector; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-27-esp-idf-refresh/${p}.quick.json"
done

# ESP-IDF deep sweeps (full heuristic set, parallel workers)
mkdir -p results/oss_validation/reports/2026-02-27-esp-idf-deep
for p in \
  esp_idf_ota_upgrade \
  esp_idf_fault_no_fallback \
  esp_idf_fault_crc_covers_state \
  esp_idf_fault_no_abort \
  esp_idf_fault_no_crc; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --workers 4 \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-27-esp-idf-deep/${p}.full.json"
done

# Bounded baseline for no_crc comparison (image_hash + bit_corruption)
cp profiles/esp_idf_ota_upgrade.yaml /tmp/esp_idf_ota_upgrade_hash_bit_bounded.yaml
python3 - <<'PY'
import yaml
path = "/tmp/esp_idf_ota_upgrade_hash_bit_bounded.yaml"
with open(path) as f:
    doc = yaml.safe_load(f)
doc.setdefault("success_criteria", {})["image_hash"] = True
fs = doc.setdefault("fault_sweep", {})
fs["fault_types"] = ["power_loss", "interrupted_erase", "bit_corruption"]
fs["max_step_limit"] = 0x180000
with open(path, "w") as f:
    yaml.safe_dump(doc, f, sort_keys=False)
PY
python3 scripts/audit_bootloader.py \
  --profile /tmp/esp_idf_ota_upgrade_hash_bit_bounded.yaml \
  --workers 4 \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output results/oss_validation/reports/2026-02-27-esp-idf-deep/esp_idf_ota_upgrade_hash_bit_bounded.full.json

# ESP-IDF copy-guard exploratory pair (non-differential in current model)
mkdir -p results/oss_validation/reports/2026-02-27-esp-idf-copy-guard
for p in \
  esp_idf_ota_upgrade_copy_guard \
  esp_idf_fault_no_crc_copy_guard; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --workers 4 \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-27-esp-idf-copy-guard/${p}.full.json"
done

# ESP-IDF CRC-guard differential pair (baseline vs no_crc)
mkdir -p results/oss_validation/reports/2026-02-27-esp-idf-crc-guard
for p in \
  esp_idf_ota_crc_guard \
  esp_idf_fault_no_crc_crc_guard; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-27-esp-idf-crc-guard/${p}.full.json"
done

# Exploratory matrix (baseline-only discovery lane)
python3 scripts/run_exploratory_matrix.py \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-v1

# Exploratory matrix (defect-inclusive, capped sample)
python3 scripts/run_exploratory_matrix.py \
  --quick \
  --include-defect-profiles \
  --max-cases 24 \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-with-defects-v1

# Exploratory matrix analyzer v2 (baseline+defect delta ranking + OtaData drift)
python3 scripts/run_exploratory_matrix.py \
  --profile profiles/esp_idf_ota_upgrade.yaml \
  --profile profiles/esp_idf_fault_no_crc.yaml \
  --profile profiles/esp_idf_ota_upgrade_copy_guard.yaml \
  --profile profiles/esp_idf_fault_no_crc_copy_guard.yaml \
  --fault-preset profile \
  --fault-preset write_erase_bit \
  --criteria-preset profile \
  --criteria-preset image_hash_exec \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-deltas-v2

# Full ESP exploratory matrix (all baseline + defect profiles)
python3 scripts/run_exploratory_matrix.py \
  --quick \
  --include-defect-profiles \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1

# Recompute matrix scoring/clustering after script-only analyzer changes
# (skips rerunning case audits and reuses existing per-case report JSONs)
python3 scripts/run_exploratory_matrix.py \
  --quick \
  --include-defect-profiles \
  --reuse-existing \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1

# Rollback guard quick pair (new OtaData criteria profile pair)
mkdir -p results/oss_validation/reports/2026-02-28-esp-idf-rollback-guard
for p in \
  esp_idf_ota_rollback_guard \
  esp_idf_fault_no_abort_rollback_guard; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --output "results/oss_validation/reports/2026-02-28-esp-idf-rollback-guard/${p}.quick.json"
done

# Focused exploratory matrix for rollback guard pair
python3 scripts/run_exploratory_matrix.py \
  --profile profiles/esp_idf_ota_rollback_guard.yaml \
  --profile profiles/esp_idf_fault_no_abort_rollback_guard.yaml \
  --fault-preset profile \
  --criteria-preset profile \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-28-esp-idf-rollback-guard-matrix-v2

# New fault-type quick smoke (`write_rejection` + `reset_at_time`)
mkdir -p results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types
for p in \
  esp_idf_ota_upgrade_write_rejection \
  esp_idf_ota_upgrade_reset_at_time; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --no-assert-control-boots \
    --no-assert-verdict \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --output "results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types/${p}.quick.json"
done

# Higher-sample non-quick sweeps for new fault types
mkdir -p results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types-full
for p in \
  esp_idf_ota_upgrade_write_rejection \
  esp_idf_ota_upgrade_reset_at_time; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --workers 4 \
    --no-assert-control-boots \
    --no-assert-verdict \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --output "results/oss_validation/reports/2026-02-28-esp-idf-new-fault-types-full/${p}.full.json"
done

# Extended guard quick batch (`ss_guard` + `crc_schema_guard`)
mkdir -p results/oss_validation/reports/2026-02-28-esp-idf-extended-guards
for p in \
  esp_idf_ota_ss_guard \
  esp_idf_fault_single_sector_ss_guard \
  esp_idf_ota_crc_schema_guard \
  esp_idf_fault_crc_covers_state_crc_schema_guard; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --no-assert-control-boots \
    --no-assert-verdict \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --output "results/oss_validation/reports/2026-02-28-esp-idf-extended-guards/${p}.quick.json"
done

# Focused matrix for new guard pairs
python3 scripts/run_exploratory_matrix.py \
  --output-dir results/exploratory/2026-02-28-esp-idf-extended-guards-matrix \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --profile profiles/esp_idf_ota_ss_guard.yaml \
  --profile profiles/esp_idf_fault_single_sector_ss_guard.yaml \
  --profile profiles/esp_idf_ota_crc_schema_guard.yaml \
  --profile profiles/esp_idf_fault_crc_covers_state_crc_schema_guard.yaml \
  --fault-preset profile \
  --criteria-preset profile

# Fallback-guard quick pair (baseline fallback vs no_fallback defect)
mkdir -p results/oss_validation/reports/2026-02-28-esp-idf-fallback-guard
for p in \
  esp_idf_ota_fallback_guard \
  esp_idf_fault_no_fallback_fallback_guard; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --no-assert-control-boots \
    --no-assert-verdict \
    --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
    --output "results/oss_validation/reports/2026-02-28-esp-idf-fallback-guard/${p}.quick.json"
done

# Focused matrix for fallback-guard pair
python3 scripts/run_exploratory_matrix.py \
  --profile profiles/esp_idf_ota_fallback_guard.yaml \
  --profile profiles/esp_idf_fault_no_fallback_fallback_guard.yaml \
  --fault-preset profile \
  --criteria-preset profile \
  --quick \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-28-esp-idf-fallback-guard-matrix

# Refresh full discovery matrix with new default profiles (reuse old reports)
python3 scripts/run_exploratory_matrix.py \
  --quick \
  --include-defect-profiles \
  --reuse-existing \
  --renode-test /Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test \
  --output-dir results/exploratory/2026-02-27-esp-idf-discovery-deltas-all-v1
```

## What Needs To Be Done

### 1. Bit Corruption Commit Status

Done. Bit-corruption runtime fault mode is already committed on this branch.

### 2. Beef Up the ESP-IDF Model (HIGH PRIORITY)

**Current status (improved, still incomplete):**

- `esp_idf_fault_no_abort`, `esp_idf_fault_no_fallback`, and `esp_idf_fault_crc_covers_state` now exercise copy-on-boot write-heavy paths (~2k writes each), and `esp_idf_fault_single_sector` is no longer stateless.
- Added `success_criteria.image_hash_slot` (slot-gated hash checks) plus hash normalization (profile image digests now pad/truncate to runtime slot data length).
- Fixed synthetic-image masking by removing app-side VTOR rewrite in `gen_esp_idf_images.py`; observed `boot_slot` now tracks bootloader decisions.
- Added two exploratory ESP pair sets:
  - `copy_guard` pair: still non-differential at deep scale (`0/727` bricks for both baseline and no_crc).
  - `crc_guard` pair: differential achieved for no_crc (`baseline 0/4` vs `no_crc 1/4`, plus no_crc control `no_boot/staging`).
- Added explicit OtaData assertion support (`success_criteria.otadata_expect`) and a rollback guard pair:
  - `esp_idf_ota_rollback_guard` (baseline) vs `esp_idf_fault_no_abort_rollback_guard` (defect)
  - Quick differential: baseline `0/4` bricks vs defect `5/5` bricks.
- Added `success_criteria.otadata_expect_scope` (`always` or `control`) to scope OtaData assertions per lane.
- Added two more exploratory guard pairs with quick differential evidence:
  - `ss_guard`: `esp_idf_ota_ss_guard` vs `esp_idf_fault_single_sector_ss_guard` (`0/4` vs `4/4` bricks).
  - `crc_schema_guard`: `esp_idf_ota_crc_schema_guard` vs `esp_idf_fault_crc_covers_state_crc_schema_guard` (control mismatch differential: `success/exec` vs `wrong_image/exec`).
- Added `fallback_guard` pair for `no_fallback`:
  - `esp_idf_ota_fallback_guard` vs `esp_idf_fault_no_fallback_fallback_guard`
  - Control divergence is now explicit (`success/exec` baseline vs `no_boot` defect).

**Remaining gap:**

- Differential evidence now exists for `no_crc` (CRC guard), `no_abort` (rollback guard), `single_sector` (`ss_guard`), `crc_covers_state` (`crc_schema_guard`), and `no_fallback` (`fallback_guard`).
- High-write copy-path differentials are still missing for `no_crc` and `no_fallback` fault-induced lanes.

**High-value next steps:**

- Expand `otadata_expect` usage and add a matrix criteria preset for OtaData-asserted lanes (including scope-aware control-only checks).
- Tune copy-path scenarios so the correct profile and defect diverge under the same high-write fault windows (not just low-write CRC-guard cases).
- Add high-write copy-on-boot variants of `fallback_guard` so `no_fallback` shows fault-induced divergence (not only control divergence).
- New fault-type baseline sweeps (`write_rejection`/`reset_at_time`) are now high-sample and clean (`0/362` each); next step is defect-targeted lanes where these modes are expected to produce differential behavior.
- Add per-lane minimum-sample thresholds for auto-allowlisting (avoid overfitting when baseline lane coverage is sparse).

### 3. More Fault Types

User explicitly requested ("uh can we do all of this?!?!?"):

- Implemented and wired end-to-end: `power_loss`, `bit_corruption`, `silent_write_failure`, `write_rejection`, `write_disturb`, `wear_leveling_corruption`, `interrupted_erase`, `multi_sector_atomicity`, `reset_at_time`.
- Practical next step is coverage depth: run targeted differential lanes where each non-default mode (`b/s/r/d/l/t`) is expected to reveal defect-specific behavior.

### 4. Additional Real-World Bootloader Differentials

From the bug classes doc at `~/mirala/mirala_docs/ota-res/mcuboot-real-world-bug-classes-and-detection-plan.md`:

- **PR #2205**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry
- **PR #2206**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry
- **PR #2214**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry (including `zephyr_slot1_max.bin`)

New exploratory profiles:

- `profiles/mcuboot_pr2205_scratch_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2206_scratch_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2214_offset_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2206_scratch_geom_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2214_offset_geom_{broken,fixed}.yaml`

These bug classes are geometry-sensitive. To make them detectable, next step is a geometry-tailored target (mixed sector map + trailer-at-boundary conditions), plus tuning image size to stay bootable on fixed revisions while still breaking on broken revisions.

### 5. Non-MCUboot Real Binary Testing

Currently MCUboot is the ONLY real (non-model) bootloader tested. All others are clean-room models. Ideally:

- ESP-IDF: Can't run in Renode (no ESP32 platform). Our model is the best we can do.
- NuttX nxboot: Could potentially build a real NuttX image for Cortex-M4. Complex NuttX build system.
- U-Boot: Huge, but some SoC targets might work in Renode.
- TF-A (ARM Trusted Firmware): Uses MCUboot internally for BL2.

### 6. CI / GitHub Actions

Direct-to-main workflow is currently in use. The remaining CI gap is still self-test automation in GitHub Actions; blocker is Renode binary distribution in CI. Likely options: Renode Docker image or portable release download step.

### 7. Result Visualization / Reporting

Currently results are JSON blobs. Could benefit from:

- HTML report with fault point heatmap (which addresses brick)
- Comparison view: broken vs fixed side by side
- Aggregated report across all profiles

### 8. Push Directly To Main

Current workflow is direct-to-main (no PR required):

- Commit incremental artifacts and scripts on `main`
- Push to `origin/main`
- Keep `HANDOFF.md` current after each batch so next agent can resume immediately

## Gotchas and Lessons Learned

1. **TRACE REPLAY FALSE POSITIVES**: Trace replay only replays writes. If you add a new fault type that depends on peripheral state (like bit corruption, or erase behavior), it MUST use full execute mode, not trace replay. We learned this the hard way with erase trace — 76 false positives because erases weren't replayed.

2. **NVMC counts CHANGED words, not all writes**: Writing 0xFF to erased flash doesn't count as a write. The diff-based counting means `TotalWordWrites` only increments for words that actually changed. Otadata-only ESP-IDF scenarios therefore sit around `3 writes / 1 erase` unless copy-on-boot stress is enabled.

3. **`emulation RunFor` NOT `cpu.Step()`**: RunFor is ~350x faster. Never use Step for anything but single-instruction debugging.

4. **MCUboot swap-scratch has 91.6% inherent brick rate**: This is by design (the algorithm), not a bug. Don't waste time trying to fix it.

5. **ELF binaries contain build paths in DWARF**: Always strip before committing to the public repo. `arm-none-eabi-strip` or `objcopy --strip-debug`.

6. **Renode-test setup mismatch**: Source-tree `renode-test` wrappers can fail with `Robot framework remote server binary not found .../output/bin/Release/Renode.exe` unless that build output exists. The packaged path (`/Users/neil/.local/renode/app/Renode.app/Contents/MacOS/renode-test`) works out of the box in this workspace.

7. **vtor_in_slot: any**: Committed feature. Means "boot to ANY defined slot = success". Useful for bootloaders with graceful fallback where either slot is acceptable.

8. **Phase 2 DiffLookahead**: Set `nvmc.DiffLookahead = 32` for recovery boot phase (no write counting needed, 10x faster). Set `int.MaxValue` for calibration/sweep.

9. **Geometry bugs need geometry triggers**: PR2205/2206/2214 are not guaranteed to reproduce on default nRF52840 partition/sector geometry. Mixed-sector layouts and trailer-at-boundary cases are often required.

10. **Threshold sweeps are expensive unless tuned**: `scripts/sweep_pr2206_geometry_threshold.py` should usually run with lower `--max-step-limit` plus `--reuse-existing` to avoid rerunning completed points. Generated `slot1_payload_*.bin` files are intermediate and can be dropped once JSON reports are captured.

11. **Bit-corruption deep chunks can tail badly**: In large parallel batches that include many `'b'` points, one worker can run much longer than the rest under default `max_step_limit=20000000`. For comparison experiments, lower step caps in profiles (or dedicated temp profiles) keep runs bounded.

12. **Synthetic app code can mask boot-slot attribution**: If test images rewrite `VTOR` internally, reported `boot_slot` may reflect app behavior rather than bootloader decision. ESP images now preserve bootloader-selected `VTOR` to avoid this trap.

13. **Heuristic reduction can hide tiny-profile failures**: For very small write counts (e.g., 3 writes), heuristic selection may skip a critical write. Use `fault_sweep.sweep_strategy: exhaustive` when you need every write point.

14. **Exploratory matrix should not gate on profile verdict assertions**: `scripts/run_exploratory_matrix.py` now invokes `audit_bootloader.py` with `--no-assert-control-boots --no-assert-verdict`. This keeps discovery lanes from dropping cases due expectation mismatches while still preserving full control/failure signals in report JSON.

15. **`run_exploratory_matrix.py` needs explicit `--renode-test` unless `renode-test` is on PATH**: Without this, cases can all show `nonzero_exit` and `cases_missing_report` due `FileNotFoundError: renode-test executable 'renode-test' not found in PATH`.

16. **Control-outcome deltas are now first-class in defect scoring**: `build_defect_deltas()` compares baseline vs defect control outcomes (`control_outcome_changed` / `control_outcome_shift`) in addition to control-mismatch-vs-expected. This prevents real regressions from being hidden when each profile has different expected control outcomes.

17. **`reset_at_time` full sweeps are slower than other write fault modes**: even with heuristic reduction and parallel workers, timed-reset campaigns can run much longer than write-reject/bit/erase lanes. Prefer `--workers` plus bounded exploratory lanes first, then scale up.

## Profile YAML Schema Quick Reference

```yaml
schema_version: 1
name: string
skip_self_test: false # optional: true to exclude exploratory profiles
description: string
platform: platforms/cortex_m4_flash_fast.repl # or cortex_m0_nvm.repl
bootloader:
  elf: path/to/bootloader.elf
  entry: 0x00000000
memory:
  sram: { start: 0x20000000, end: 0x20040000 }
  write_granularity: 4 # bytes per write (4 for NVMC, 8 for NVMemory)
  slots:
    exec: { base: 0x0000C000, size: 0x74000 }
    staging: { base: 0x00080000, size: 0x74000 }
images:
  exec: path/to/exec_image.bin # optional
  staging: path/to/staging_image.bin
pre_boot_state: # static flash writes before boot
  - { address: 0x000F8000, u32: 0x00000001 }
# setup_script: scripts/foo.resc   # alternative: run Renode commands
success_criteria:
  vtor_in_slot: exec # or staging, or any, or omit for "any boot = success"
  # pc_in_slot: exec    # optional
  # image_hash: true    # optional: SHA-256 of exec slot
  # expected_image: staging # optional: which profile image exec should match
  # image_hash_slot: exec   # optional: only enforce image_hash when boot_slot matches
  # marker_address: 0x... # optional: app-written marker
  # marker_value: 0x...   # optional
  # otadata_expect_scope: always # optional: always or control
  # otadata_expect:        # optional: post-boot OtaData signal assertions
  #   otadata_available: true
  #   otadata_active_entry: entry1
  #   otadata0_state_name: VALID
  #   otadata1_state_name: [ABORTED, UNDEFINED] # scalar or list accepted
fault_sweep:
  mode: runtime
  evaluation_mode: execute # or state, or omit for auto
  sweep_strategy: heuristic # or exhaustive
  max_writes: auto # or integer
  max_writes_cap: 200000
  run_duration: "2.0"
  max_step_limit: 20000000
  fault_types: [power_loss, interrupted_erase, bit_corruption, write_rejection, reset_at_time]
expect:
  should_find_issues: true
  brick_rate_min: 0.5 # optional minimum brick rate
  control_outcome: success # optional expected control boot outcome
```
