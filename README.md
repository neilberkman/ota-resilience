# ota-resilience

Power-loss fault injection testbed for OTA firmware updates under Renode.

## What this is

A framework for testing whether your firmware survives power loss at every
write point during an OTA update. You bring your firmware and OTA logic,
wire up a scenario script, and the campaign runner sweeps every write index
through Renode with a simulated fault.

## Included examples

Two built-in scenarios:

| Scenario     | Strategy                                   | Brick rate | Why                                              |
| ------------ | ------------------------------------------ | ---------- | ------------------------------------------------ |
| `vulnerable` | Copy-in-place, no checks                   | ~88%       | Overwrites only image; any mid-copy fault bricks |
| `resilient`  | A/B slots + bootloader + metadata replicas | 0%         | Active slot never touched during update          |

```mermaid
flowchart LR
    subgraph V["vulnerable"]
        V1[Copy staging → active] -->|power loss| V2[BRICK]
    end
    subgraph R["resilient"]
        R1[Write to inactive slot B] -->|power loss| R2[Slot A still valid → OK]
        R1 -->|completes| R3[Flip metadata → OK]
    end

    style V2 fill:#d32f2f,color:#fff
    style R2 fill:#388e3c,color:#fff
    style R3 fill:#388e3c,color:#fff
```

See [docs/architecture.md](docs/architecture.md) for detailed flow diagrams
and NVM memory layout.

## What this project provides

- Custom Renode NVM peripheral with persistent backing store across reset:
  `peripherals/NVMemoryController.cs`
- Fault-point scenario execution for vulnerable and resilient flows:
  `scripts/run_vulnerable_fault_point.resc`, `scripts/run_resilient_fault_point.resc`
- Canonical campaign runner using Robot + `renode-test` with thin Python orchestration:
  `tests/ota_fault_point.robot`, `scripts/ota_fault_campaign.py`
- Campaign reports and comparative table generation:
  `results/campaign_report.json`, `results/comparative_table.txt`

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
cd examples/vulnerable_ota && make
cd ../resilient_ota && make
```

Requires `arm-none-eabi-gcc` on `PATH`.

For physical Cortex-M0+ targets, enable VTOR relocation in the resilient
bootloader build:

```bash
make -C examples/resilient_ota CFLAGS="-DENABLE_VTOR_RELOCATION=1 ${CFLAGS}"
```

The bootloader defaults this to `0` so the same source still builds for
cores without VTOR.

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
├── peripherals/NVMemoryController.cs
├── platforms/cortex_m0_nvm.repl
├── scripts/
├── examples/
├── tests/
├── docs/
└── results/
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
