# Getting started

## Prerequisites

- Renode >= 1.15
- Python 3.8+
- Optional for rebuilding examples: Arm GNU toolchain (`arm-none-eabi-gcc`) on `PATH`

## Build example firmware (optional)

Prebuilt example binaries are committed in `examples/`, so you can run campaigns
without rebuilding. Rebuild only if you modify firmware sources.

```bash
cd examples/vulnerable_ota && make
cd ../resilient_ota && make
```

## Verify installation

Run the NVM peripheral unit tests to confirm Renode and renode-test are
working correctly:

```bash
renode-test tests/nvm_peripheral.robot
```

Expected: all 5 test cases pass (persistence, word-write semantics,
partial write corruption, NV read alias, NV write drop). If `renode-test` is not on
your `PATH`, set `RENODE_TEST=/full/path/to/renode-test`.

## Smoke-load in Renode

```bash
renode --console --disable-gui --execute "i @scripts/load_vulnerable.resc; quit"
renode --console --disable-gui --execute "i @scripts/load_resilient.resc; quit"
```

## Run comparative campaign

```bash
python3 scripts/ota_fault_campaign.py \
  --scenario comparative \
  --evaluation-mode execute \
  --fault-range 0:28160 \
  --fault-step 5000 \
  --output results/campaign_report.json \
  --table-output results/comparative_table.txt
```

If `renode-test` is not on your `PATH`, set `RENODE_TEST` to the full binary path.
Use `--evaluation-mode state` for faster, state-only sweeps.

## Update README comparative table from live report

```bash
python3 scripts/update_readme_from_report.py \
  --report results/campaign_report.json \
  --readme README.md
```

## Run Robot tests

`tests/nvm_peripheral.robot` validates NVM model behavior.
`tests/ota_resilience.robot` validates campaign-level resilience expectations.

## Outcome taxonomy

Campaign results classify each fault point into one of four outcomes:

| Outcome      | Meaning                                                                                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `success`    | Firmware boots from a valid slot. The bootloader found a slot with a valid vector table (SP in SRAM range, reset vector in slot range with thumb bit set). |
| `hard_fault` | Vector table corrupted and no valid fallback slot exists. Device is bricked.                                                                               |
| `hang`       | CPU stalled without reaching a boot outcome. Detected by test harness timeout.                                                                             |
| `error`      | Test infrastructure failure (renode-test crash, missing file, etc). Not a firmware outcome.                                                                |

The vulnerable copy-based OTA produces `hard_fault` at every fault point
except the last (where the copy completes before the fault). The resilient
A/B bootloader produces `success` at every fault point because it never
overwrites the running image.

See `docs/architecture.md` for detailed flow diagrams.
