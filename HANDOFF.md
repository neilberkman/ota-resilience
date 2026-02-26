# OTA Resilience — Agent Handoff Document

## What This Project Is

A Renode-based fault injection testbed for OTA firmware updates. It simulates power loss (and other faults) at every NVM write/erase point during a bootloader's update process, then checks if the device can still boot. If it can't boot after the fault, that's a "brick" — a real-world vulnerability.

**Public repo**: `git@github.com:neilberkman/ota-resilience.git`

**CARDINAL RULE**: This is a **clean room public repo**. ZERO proprietary info. No company names, no internal peripheral names, no private firmware paths. EVER. See MEMORY.md for the nuclear lesson about IP contamination.

## Architecture Overview

```
profiles/*.yaml          -- Declarative bootloader profiles (51 total: 45 self-test + 6 exploratory)
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

### Branch: `erase-trace-replay-fix` (active development branch)

- Last main-repo commit: `117a084` — OSS validation assets for MCUboot PR2205/2206/2214 + near-max slot image
- Working tree: clean at commit time of this handoff update
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
| ESP-IDF OTA           | Model                    | 8 (3 baseline + 5 defect variants)                               | Clean-room otadata algorithm, too simple       |

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

| Profile Name        | Code  | Implemented            | How It Works                                                                                                                          |
| ------------------- | ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `power_loss`        | `'w'` | Yes                    | Block the Nth write entirely. Flash snapshot has N-1 writes completed.                                                                |
| `interrupted_erase` | `'e'` | Yes                    | Partial erase at Nth erase: first half 0xFF, second half untouched.                                                                   |
| `bit_corruption`    | `'b'` | Yes                    | NOR flash physics: partially program the Nth write. ~50% of 1→0 bit transitions complete, rest stay at 1. Deterministic via LCG PRNG. |
| `write_rejection`   | —     | No                     | Future: erase-before-write violation                                                                                                  |
| `reset_at_time`     | —     | No                     | Future: arbitrary-time reset, not just at write boundary                                                                              |

### Bit Corruption Details (committed)

`NRF52NVMC.cs` properties:

- `WriteFaultMode`: 0 = power_loss (default), 1 = bit_corruption
- `CorruptionSeed`: deterministic PRNG seed (0 = use TotalWordWrites)

NOR flash physics: erased = all 1s. Programming flips bits 1→0. Interrupted programming = only SOME intended 1→0 transitions complete. Implementation: `corruptedWord = oldWord & ~(bitsToFlip & prgn_mask)` where `bitsToFlip = oldWord & ~newWord`.

Bit corruption and erase faults are forced through full execute mode (not trace replay) because they depend on NVMC peripheral state at the exact fault moment.

## Running Things

### Prerequisites

- Renode: binary at `/Users/neil/.local/bin/renode`
- renode-test: `/Users/neil/mirala/renode/renode-test`
- Server dir: `/tmp/renode-server` with `Renode.exe` symlink + `build_type` file
- ARM toolchain: `~/tools/gcc-arm-none-eabi-8-2018-q4-major/bin/`
- Python 3.x with PyYAML

### Commands

```bash
# Self-test (all 45 profiles, ~45 min with --quick)
python3 scripts/self_test.py \
  --renode-test /Users/neil/mirala/renode/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --quick

# Single profile audit
python3 scripts/audit_bootloader.py \
  --profile profiles/mcuboot_head_upgrade.yaml \
  --quick \
  --renode-test /Users/neil/mirala/renode/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output /tmp/result.json

# With parallel workers (faster for large write counts)
python3 scripts/audit_bootloader.py \
  --profile profiles/mcuboot_pr2109_scratch_broken.yaml \
  --workers 4 \
  --renode-test /Users/neil/mirala/renode/renode-test \
  --renode-remote-server-dir /tmp/renode-server \
  --output /tmp/result.json

# Build ESP-IDF variants
cd examples/esp_idf_ota && make clean && make all && make strip

# Quick differential batch for PR2205/2206/2214 exploratory profiles
mkdir -p results/oss_validation/reports/2026-02-26-pr2205-2206-2214
for p in \
  mcuboot_pr2205_scratch_broken mcuboot_pr2205_scratch_fixed \
  mcuboot_pr2206_scratch_broken mcuboot_pr2206_scratch_fixed \
  mcuboot_pr2214_offset_broken mcuboot_pr2214_offset_fixed; do
  python3 scripts/audit_bootloader.py \
    --profile "profiles/${p}.yaml" \
    --quick \
    --renode-test /Users/neil/mirala/renode/renode-test \
    --renode-remote-server-dir /tmp/renode-server \
    --output "results/oss_validation/reports/2026-02-26-pr2205-2206-2214/${p}.quick.json"
done
```

## What Needs To Be Done

### 1. Bit Corruption Commit Status

Done. Bit-corruption runtime fault mode is already committed on this branch.

### 2. Beef Up the ESP-IDF Model (HIGH PRIORITY)

**The problem**: The ESP-IDF OTA model only does 3 flash writes and 1 erase during a boot. That's because it only updates the 32-byte otadata entry, and only 3 of those 8 words differ from erased state. This means:

- The 5 defect variants (`NO_CRC`, `SINGLE_SECTOR`, `NO_ABORT`, `NO_FALLBACK`, `CRC_COVERS_STATE`) all show `should_find_issues: false` — the fault model can't distinguish them from the correct implementation
- Bit corruption produces identical results to power-loss because both slots always have valid firmware
- The vulnerability window is too narrow for meaningful testing

**What the real ESP-IDF bootloader does that our model doesn't**:

- Image hash validation (reads entire slot, computes SHA-256)
- Secure boot signature verification
- Writes verification status to otadata after checking
- Multiple state transitions across boot cycles

**Possible approaches**:

- Add image copy phase (bootloader copies firmware from staging → exec before booting). Creates hundreds of writes. But this overlaps with naive_copy models.
- Add image hash validation (CRC or SHA-256 check of the selected slot before booting, write "verified" flag). More writes + reads.
- Add a multi-stage update simulation: erase target → write image → write header → update otadata. The "OTA agent" phase happens in-bootloader.
- Best: make the bootloader actually DO the update (erase + copy + validate + commit), not just select a pre-staged slot. This is how some real bootloaders work (copy-on-boot pattern like MCUboot).

**Goal**: The no-CRC defect should be DETECTABLE — bit corruption during hash/CRC writes should cause the bootloader to accept corrupted data without CRC, while the correct version rejects it.

### 3. More Fault Types

User explicitly requested ("uh can we do all of this?!?!?"):

- **Silent write failure**: Write appears to succeed but value is all-0xFF or all-0x00. Different from bit corruption (which partially programs). Would catch bootloaders that don't verify writes.
- **Write disturb**: Writing one cell disturbs adjacent cells. Would catch bootloaders with insufficient wear-leveling or sector isolation.
- **Multi-sector atomicity failures**: Fault during multi-sector operations where partial completion leaves inconsistent state across sectors.
- **Wear leveling corruption**: NOR flash cells degrade after many erase cycles. Simulated via probabilistic bit errors on aged sectors.

Implementation pattern: Add new values to `WriteFaultMode` in `NRF52NVMC.cs`, add profile schema `fault_types` values in `profile_loader.py`, add dispatch in `run_runtime_fault_sweep.resc`.

### 4. Additional Real-World Bootloader Differentials

From the bug classes doc at `~/mirala/mirala_docs/ota-res/mcuboot-real-world-bug-classes-and-detection-plan.md`:

- **PR #2205**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry
- **PR #2206**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry
- **PR #2214**: Built + quick-audited (broken/fixed), no quick differential on nRF52840 geometry (including `zephyr_slot1_max.bin`)

New exploratory profiles:

- `profiles/mcuboot_pr2205_scratch_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2206_scratch_{broken,fixed}.yaml`
- `profiles/mcuboot_pr2214_offset_{broken,fixed}.yaml`

These bug classes are geometry-sensitive. To make them detectable, next step is a geometry-tailored target (mixed sector map + trailer-at-boundary conditions), not just commit-pair swaps on default nRF52840 layout.

### 5. Non-MCUboot Real Binary Testing

Currently MCUboot is the ONLY real (non-model) bootloader tested. All others are clean-room models. Ideally:

- ESP-IDF: Can't run in Renode (no ESP32 platform). Our model is the best we can do.
- NuttX nxboot: Could potentially build a real NuttX image for Cortex-M4. Complex NuttX build system.
- U-Boot: Huge, but some SoC targets might work in Renode.
- TF-A (ARM Trusted Firmware): Uses MCUboot internally for BL2.

### 6. CI / GitHub Actions

PR #1 is open (or was). The self-test should run in CI. Current blocker: Renode binary distribution for CI. May need to use Renode's Docker image or download the portable release.

### 7. Result Visualization / Reporting

Currently results are JSON blobs. Could benefit from:

- HTML report with fault point heatmap (which addresses brick)
- Comparison view: broken vs fixed side by side
- Aggregated report across all profiles

### 8. Push + Update PR

Main branch contains additional local commits (including PR2205/2206/2214 assets). Push branch and update PR with:

- Newly added MCUboot assets in `results/oss_validation/assets/`
- Exploratory profile set for PR2205/2206/2214
- Exploratory quick reports in `results/oss_validation/reports/2026-02-26-pr2205-2206-2214/`

## Gotchas and Lessons Learned

1. **TRACE REPLAY FALSE POSITIVES**: Trace replay only replays writes. If you add a new fault type that depends on peripheral state (like bit corruption, or erase behavior), it MUST use full execute mode, not trace replay. We learned this the hard way with erase trace — 76 false positives because erases weren't replayed.

2. **NVMC counts CHANGED words, not all writes**: Writing 0xFF to erased flash doesn't count as a write. The diff-based counting means `TotalWordWrites` only increments for words that actually changed. This is why the ESP-IDF model shows 3 writes instead of 8.

3. **`emulation RunFor` NOT `cpu.Step()`**: RunFor is ~350x faster. Never use Step for anything but single-instruction debugging.

4. **MCUboot swap-scratch has 91.6% inherent brick rate**: This is by design (the algorithm), not a bug. Don't waste time trying to fix it.

5. **ELF binaries contain build paths in DWARF**: Always strip before committing to the public repo. `arm-none-eabi-strip` or `objcopy --strip-debug`.

6. **Renode-test setup**: Needs `/tmp/renode-server/Renode.exe` (symlink to actual binary) and `/tmp/renode-server/build_type` (contains "none"). Without these, renode-test fails silently.

7. **vtor_in_slot: any**: Committed feature. Means "boot to ANY defined slot = success". Useful for bootloaders with graceful fallback where either slot is acceptable.

8. **Phase 2 DiffLookahead**: Set `nvmc.DiffLookahead = 32` for recovery boot phase (no write counting needed, 10x faster). Set `int.MaxValue` for calibration/sweep.

9. **Geometry bugs need geometry triggers**: PR2205/2206/2214 are not guaranteed to reproduce on default nRF52840 partition/sector geometry. Mixed-sector layouts and trailer-at-boundary cases are often required.

## Profile YAML Schema Quick Reference

```yaml
schema_version: 1
name: string
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
  # image_hash: true    # optional: SHA-256 of exec slot vs expected
  # marker_address: 0x... # optional: app-written marker
  # marker_value: 0x...   # optional
fault_sweep:
  mode: runtime
  evaluation_mode: execute # or state, or omit for auto
  max_writes: auto # or integer
  max_writes_cap: 200000
  run_duration: "2.0"
  max_step_limit: 20000000
  fault_types: [power_loss, interrupted_erase, bit_corruption]
expect:
  should_find_issues: true
  brick_rate_min: 0.5 # optional minimum brick rate
  control_outcome: success # optional expected control boot outcome
```
