# Fault injection

The harness includes:

- `scripts/fault_inject.py`: shared data structures and range parsing.
- `tests/ota_fault_point.robot`: canonical per-point live run entrypoint.
- `scripts/run_vulnerable_fault_point.resc`: vulnerable scenario state evaluation.
- `scripts/run_resilient_fault_point.resc`: resilient scenario state evaluation.
- `scripts/ota_fault_campaign.py`: thin Python orchestrator over `renode-test`.
- `scripts/update_readme_from_report.py`: README chart/metadata renderer.

## Canonical flow

1. `ota_fault_campaign.py` chooses fault points.
2. For each fault point, it invokes `renode-test tests/ota_fault_point.robot`.
3. The Robot suite executes scenario-specific `.resc` logic and writes a JSON result.
4. The Python orchestrator aggregates all per-point JSON files into one report.
5. `update_readme_from_report.py` renders chart + command/commit metadata into README.

## Example run

```bash
python3 scripts/ota_fault_campaign.py \
  --scenario comparative \
  --fault-range 0:28672 \
  --fault-step 5000 \
  --output results/campaign_report.json \
  --table-output results/comparative_table.txt

python3 scripts/update_readme_from_report.py \
  --report results/campaign_report.json \
  --readme README.md
```

The campaign JSON output includes per-point state-based outcomes, summary rates,
execution command metadata, and git metadata.
