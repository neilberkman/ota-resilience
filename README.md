# ota-resilience

Power-loss fault injection testbed for OTA firmware updates under Renode.

## What this is

A framework for testing whether your firmware survives power loss at every
write point during an OTA update. You bring your firmware and OTA logic,
wire up a scenario script, and the campaign runner sweeps every write index
through Renode with a simulated fault.

## Included bootloader families

Four bootloader architectures, from worst-case to fully resilient:

| Family         | Architecture                        | Brick rate | Why                                          |
| -------------- | ----------------------------------- | ---------- | -------------------------------------------- |
| `naive_copy`   | Copy staging to exec, no fallback   | ~100%      | Any mid-copy fault bricks; no recovery path  |
| `vulnerable`   | Copy-in-place with pending flag     | ~88%       | Overwrites only image; mid-copy fault bricks |
| `nxboot_style` | Three-partition copy, CRC, recovery | ~0%        | Recovery slot enables revert on corruption   |
| `resilient`    | A/B slots + metadata replicas       | 0%         | Active slot never touched during update      |

### Intentional-defect variants

Each family includes defect variants for self-testing (proving the audit tool
detects known bugs):

- **fault_variants/** (11 variants): no_fallback, no_vector_check, crc_off_by_one,
  both_replicas_race, seq_naive, no_boot_count, and MCUboot-modeled defects
- **naive_copy/** (3 variants): bare_copy, crc_pre_copy, crc_post_copy
- **nxboot_style/** (4 variants): correct, no_recovery, no_revert, no_crc

### OSS validation targets

- **MCUboot** (swap-using-move on nRF52840): pre-built ELFs from CI, known-good
  and known-bad commit guards
- **NuttX nxboot** (modeled): three-partition copy-based bootloader with
  magic-flip commit protocol

See [docs/architecture.md](docs/architecture.md) for flow diagrams and memory layout.

## What this project provides

- **Unguided bootloader audit**: `scripts/audit_bootloader.py` -- state-space
  fuzzing + fault injection to find brick conditions automatically
- **Self-test harness**: `scripts/self_test.py` -- validates the audit tool
  catches all known defects across 18 bootloader variants
- **OSS validation**: `scripts/run_oss_validation.py` -- runs named profiles
  against real OSS bootloaders (MCUboot, nxboot)
- **NVM peripheral**: `peripherals/NVMemoryController.cs` -- persistent
  non-volatile memory with partial-write fault injection
- **MCUboot state fuzzer**: `scripts/mcuboot_state_fuzzer.py` -- property-based
  trailer state exploration with oracle predictions
- **Campaign runner**: `scripts/ota_fault_campaign.py` + Robot suites

## Design principles

- Live Renode-first execution (no simulate-first campaign path).
- State-based outcomes (slot/metadata/memory markers), not log text heuristics.
- Keep custom logic only where it adds value:
  `NVMemoryController.cs` + OTA scenario logic.
- Reproducible CI with pinned Renode action, Renode revision, and toolchain.

## Quick start

Prerequisites:

- `python3`
- `renode-test` available on `PATH` (or set `RENODE_TEST=/full/path/to/renode-test`)

Run comparative campaign:

```bash
python3 scripts/ota_fault_campaign.py \
  --scenario comparative \
  --fault-range 0:28672 \
  --fault-step 5000 \
  --evaluation-mode execute \
  --output results/campaign_report.json \
  --table-output results/comparative_table.txt
```

For fast local iteration, use `--quick` (first/middle/last fault points) and
`--evaluation-mode state`. Use `execute` mode for final validation.

Refresh README comparative table block from live report:

```bash
python3 scripts/update_readme_from_report.py \
  --report results/campaign_report.json \
  --readme README.md
```

Prebuilt example `.elf` and `.bin` artifacts are committed, so clone-and-run
works without a cross-compiler.

## Optional firmware rebuild

If you modify example firmware sources:

```bash
make -C examples/vulnerable_ota
make -C examples/resilient_ota
make -C examples/fault_variants
make -C examples/naive_copy
make -C examples/nxboot_style
python3 examples/nxboot_style/gen_nxboot_images.py --output-dir examples/nxboot_style
```

Requires `arm-none-eabi-gcc` on `PATH`. Prebuilt ELFs are committed so
clone-and-run works without a cross-compiler.

## Validation and tests

Run campaign-level and peripheral tests:

```bash
renode-test tests/nvm_peripheral.robot
renode-test tests/ota_resilience.robot
```

By default, campaign runs include an unfaulted control point and fail if that
control does not boot. Disable with `--no-assert-control-boots` when explicitly
debugging broken baseline images.

The `tests/ota_resilience.robot` suite parses report JSON and asserts structured
fields (not serialized string matching).

Render HTML summaries from audit/self-test/matrix JSON outputs:

```bash
python3 scripts/render_results_html.py \
  --input results/exploratory/<run>/matrix_results.json \
  --output results/exploratory/<run>/matrix_report.html

# Multiple --input values produce a combined matrix dashboard section.
python3 scripts/render_results_html.py \
  --input results/exploratory/<run1>/matrix_results.json \
  --input results/exploratory/<run2>/matrix_results.json \
  --output results/exploratory/matrix_dashboard.html
```

## CI and reproducibility

- Workflow: `.github/workflows/ci.yml`
- Pinned action: `antmicro/renode-test-action@0705567acf04d7b998d7deac1e05d9067d70d901`
- Pinned Renode revision: `d66b0c2aa3d420408eccecfd1d3bab0fd702a6db`
- Pinned toolchain: xPack `13.2.1-1.1` with SHA256 verification

## Testing your own firmware

The examples are starting points. To test your OTA implementation:

1. Write a `.resc` scenario script that models your update flow
   (see `scripts/run_vulnerable_fault_point.resc` for the pattern).
2. Define success/failure by reading NVM state (slot markers, metadata,
   vector tables) -- not log text.
3. Replace example ELFs/bins with your build outputs, or load them in your `.resc`.
4. Run the campaign over your write range:

```bash
python3 scripts/ota_fault_campaign.py \
  --scenario your_scenario \
  --robot-suite tests/ota_fault_point.robot \
  --fault-range 0:YOUR_TOTAL_WRITES \
  --fault-step 100 \
  --total-writes YOUR_TOTAL_WRITES \
  --scenario-loader-script /abs/path/to/load_my_scenario.resc \
  --fault-point-script /abs/path/to/run_my_fault_point.resc \
  --robot-var PLATFORM_REPL:/abs/path/to/platform.repl \
  --robot-var VULNERABLE_FIRMWARE_ELF:/abs/path/to/firmware.elf \
  --robot-var VULNERABLE_STAGING_IMAGE:/abs/path/to/update.bin \
  --output results/your_report.json
```

If you prefer, provide your own `.robot` suite via `--robot-suite` instead of
using `tests/ota_fault_point.robot`.

The NVM peripheral and fault injection model work with any Cortex-M firmware
that writes to non-volatile memory (MRAM, flash, FRAM, etc.). You just need to
tell it what "success" and "failure" look like for your design.

## Repository layout

```text
ota-resilience/
├── peripherals/NVMemoryController.cs       # Custom NVM peripheral for Renode
├── platforms/                              # Renode platform descriptions
│   ├── cortex_m0_nvm.repl                  # Generic Cortex-M0+ with 512KB NVM
│   └── nrf52840_nvmc_psel.repl             # nRF52840 for MCUboot testing
├── scripts/
│   ├── audit_bootloader.py                 # Unguided bootloader resilience audit
│   ├── self_test.py                        # Meta-test: validate audit catches defects
│   ├── render_results_html.py              # HTML summaries for audit/self-test/matrix JSON
│   ├── run_oss_validation.py               # OSS profile orchestrator
│   ├── mcuboot_state_fuzzer.py             # MCUboot trailer state exploration
│   ├── ota_fault_campaign.py               # Fault sweep campaign runner
│   └── geometry_matrix.py                  # Multi-geometry configuration matrix
├── examples/
│   ├── naive_copy/                         # Worst-case: copy-to-address, no bootloader
│   ├── vulnerable_ota/                     # Copy-in-place with pending flag
│   ├── nxboot_style/                       # NuttX nxboot three-partition model
│   ├── resilient_ota/                      # Full A/B with metadata replicas
│   └── fault_variants/                     # 11 intentional-defect variants
├── tests/                                  # Robot Framework test suites
├── docs/                                   # Architecture, guides, dirty-room prompt
└── results/oss_validation/assets/          # Pre-built MCUboot ELFs + slot images
```

## Limitations

- Fault model is at write-operation granularity, not analog brownout simulation.
- Example outcomes model representative OTA behaviors; adapt markers for your firmware.
- If the repository has no commits yet, report metadata shows
  `unavailable (no commits yet)` for commit hash.

## Documentation

- [Getting started](docs/getting_started.md) -- prerequisites, installation verification, running campaigns
- [Architecture](docs/architecture.md) -- NVM layout, OTA flow diagrams, fault injection model
- [NVM model](docs/nvm_model.md) -- peripheral semantics, register map, read-only alias
- [Fault injection](docs/fault_injection.md) -- campaign runner, Robot integration, report rendering
- [Results schema](results/README.md) -- JSON report format and outcome taxonomy
- [Contributing](CONTRIBUTING.md) -- adding scenarios, modifying the NVM model, reporting results

## License

Apache 2.0. See `LICENSE`.
