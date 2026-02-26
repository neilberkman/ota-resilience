# Getting started

## Prerequisites

- Renode >= 1.15
- Python 3.8+
- Optional for rebuilding examples: Arm GNU toolchain (`arm-none-eabi-gcc`) on `PATH`

## Build example firmware (optional)

Prebuilt example binaries are committed in `examples/`, so you can run campaigns
without rebuilding. Rebuild only if you modify firmware sources.

```bash
make -C examples/vulnerable_ota
make -C examples/resilient_ota
make -C examples/fault_variants
make -C examples/naive_copy
make -C examples/nxboot_style
python3 examples/nxboot_style/gen_nxboot_images.py --output-dir examples/nxboot_style
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
  --fault-range 0:13824 \
  --fault-step 5000 \
  --output results/campaign_report.json \
  --table-output results/comparative_table.txt
```

If `renode-test` is not on your `PATH`, set `RENODE_TEST` to the full binary path.

## Update README comparative table from live report

```bash
python3 scripts/update_readme_from_report.py \
  --report results/campaign_report.json \
  --readme README.md
```

## Run the unguided bootloader audit

The audit tool systematically explores the state x fault space of any
bootloader to find brick conditions:

```bash
# Audit the built-in resilient bootloader (should find 0 bricks):
python3 scripts/audit_bootloader.py \
    --bootloader-elf examples/resilient_ota/bootloader.elf \
    --output results/audit_report.json

# Audit a naive copy bootloader (should find many bricks):
python3 scripts/audit_bootloader.py \
    --bootloader-elf examples/naive_copy/bootloader_bare_copy.elf \
    --output results/naive_audit.json

# Quick mode (fewer scenarios):
python3 scripts/audit_bootloader.py --quick --output /tmp/smoke.json
```

## Run the self-test (validate the audit tool itself)

The self-test runs audits against all 18 bootloader variants and checks that
the tool correctly identifies defects in broken variants and reports no issues
for correct ones:

```bash
python3 scripts/self_test.py --quick --output results/self_test_summary.json
```

## Render HTML report

Generate a visual summary (fault-point heatmap + per-profile metrics):

```bash
# Render from one or more audit outputs:
python3 scripts/render_results_html.py \
  --input /tmp/result_a.json \
  --input /tmp/result_b.json \
  --output results/audit_report.html

# Render self-test summary:
python3 scripts/render_results_html.py \
  --input results/self_test_summary.json \
  --output results/self_test_report.html
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
