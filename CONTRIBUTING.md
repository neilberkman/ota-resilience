# Contributing

## Adding a new fault scenario

1. Create a `.resc` script in `scripts/` that implements the OTA write
   sequence and fault injection logic. Use `InjectPartialWrite` from the
   NVM controller to simulate power loss at a specific write index.

2. The script must write a JSON result to `$result_file` with at minimum:
   `fault_at`, `boot_outcome`, `boot_slot`, and `nvm_state`.

3. Add a load keyword in `tests/builtin_fault_point.robot` for the new scenario
   name, following the existing `Load Built-In Vulnerable Scenario` / `Load Built-In Resilient
Scenario` pattern.

4. If your scenario is built-in, wire it in `scripts/ota_fault_campaign.py`.
   External scenarios can run directly via `--scenario <name>` with a custom
   Robot suite.

5. Determine boot outcome from NVM state (vector table validity, metadata
   CRC, slot markers). Do not parse log text.

## Modifying the NVM model

`peripherals/NVMemoryController.cs` contains two classes:

- `LocalNVMemory`: the persistent backing store. Writes go through
  word-aligned erase/program cycles. `Reset()` intentionally preserves
  storage contents.
- `NVMemoryController`: register block + fault injection API
  (`InjectFault`, `InjectPartialWrite`).

Key constraints:

- `WordSize` must be a power of two (default 8 bytes).
- `ReadOnly` instances silently drop writes (used for the NV read alias).
- `AliasTarget` delegates all operations to the target instance.
- `EnforceWordWriteSemantics` controls whether writes go through the
  erase/program cycle or bypass directly.

The platform description (`platforms/cortex_m0_nvm.repl`) maps the memory
instances and aliases. If you change the NVM geometry, update the address
constants in both the `.repl` file and the firmware sources.

## Reporting results

Campaign output goes to `results/`. The JSON schema is documented in
`results/README.md`.

To regenerate the README comparative table from a live campaign:

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

Commit updated `results/campaign_report.json` and `results/comparative_table.txt`
alongside any behavioral changes.

## Style

- Keep campaign outcomes execution-backed or state-evaluated, never log-text heuristics.
- Preserve `renode-test` as the canonical execution path (no simulate-first shortcuts).
- Robot tests validate structured JSON fields, not string matching on serialized output.
- No badges, emoji, or boilerplate in docs.
