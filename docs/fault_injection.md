# Fault injection

The harness includes:

- `scripts/fault_inject.resc`: reusable watchpoint-based fault injector.
- `tests/builtin_fault_point.robot`: built-in per-point live run entrypoint.
- `tests/generic_fault_point.robot`: generic per-point live run entrypoint for external firmware.
- `scripts/run_vulnerable_fault_point.resc`: vulnerable scenario evaluator/executor.
- `scripts/run_resilient_fault_point.resc`: resilient scenario evaluator/executor.
- `scripts/ota_fault_campaign.py`: thin Python orchestrator over `renode-test`.
- `scripts/run_oss_validation.py`: named-profile wrapper for repeatable external OSS validations.
- `scripts/update_readme_from_report.py`: README chart/metadata renderer.

## Canonical flow

1. `ota_fault_campaign.py` chooses fault points.
2. For each fault point, it invokes a Robot suite (built-in default is `renode-test tests/builtin_fault_point.robot`).
3. The Robot suite executes scenario-specific `.resc` logic and writes a JSON result.
4. The Python orchestrator aggregates all per-point JSON files into one report.
5. `update_readme_from_report.py` renders chart + command/commit metadata into README.

## Example run

```bash
python3 scripts/ota_fault_campaign.py \
  --scenario comparative \
  --evaluation-mode execute \
  --fault-range 0:28160 \
  --fault-step 5000 \
  --output results/campaign_report.json \
  --table-output results/comparative_table.txt

python3 scripts/update_readme_from_report.py \
  --report results/campaign_report.json \
  --readme README.md
```

`--evaluation-mode` controls how each point is judged:

- `execute` (default): run the boot path in Renode and evaluate using runtime markers + metadata.
- `state`: evaluate directly from NVM state without CPU execution.

By default, each scenario run also executes one unfaulted control point
(`fault_at` is set to a high sentinel beyond campaign writes) to prove the
intact image path boots. Control points are tagged with `is_control: true` and
excluded from brick-rate summary math. Use `--no-control` to disable this.

CI assertion flags:

- `--assert-no-bricks`: exit `1` if any non-control point has `boot_outcome != success`.
- `--assert-control-boots`: exit `1` if any control point does not boot successfully.
- `--trace-execution`: opt-in instruction-level execution traces for manual debugging.

Exit codes:

- `0`: success
- `1`: assertion failure
- `2`: infrastructure failure

The campaign JSON output includes per-point outcomes (including control tags),
summary rates, selected evaluation mode, execution command metadata, and git
metadata.

For A/B fault scripts (`run_bootloader_ab_fault_point.resc`), each result also
includes `fault_diagnostics`:

- always present as an object (`{}` when no fault fired)
- includes writeback bytes read from the fault address
- classifies fault region (`image_header`, `vector_table`, `payload`,
  `metadata_replica_0`, `metadata_replica_1`, `outside_slot`)
- includes expected bytes where the script can determine what should have been written
- when trace mode is enabled, includes `execution_trace` path per faulted point

Trace mode details:

- trace starts only for the post-reset boot run (not setup/write loops)
- traces are saved under `<output_stem>_traces/` beside the campaign JSON output
- trace files are kept even if `--keep-run-artifacts` is not set

For headerized A/B images (e.g. MCUboot-style staged binaries), use:

- `--boot-mode swap` for swap-style staging semantics (or `direct` for direct-slot boot).
- `--slot-a-image-file /path/to/image.bin` when slot A must also be a headerized image.
- `--slot-b-image-file /path/to/image.bin` to write a pre-built slot image directly.
- `--ota-header-size N` to validate vectors at `slot_base + N` instead of offset `0`.
