# Results JSON schema

Campaign reports are produced by `scripts/ota_fault_campaign.py` and consumed
by `tests/ota_resilience.robot` and `scripts/update_readme_from_report.py`.

## Top-level fields

| Field                     | Type   | Description                                         |
| ------------------------- | ------ | --------------------------------------------------- |
| `engine`                  | string | Always `"renode-test"` for live runs                |
| `scenario`                | string | Built-in or custom scenario name                    |
| `total_writes`            | mixed  | Int for single-scenario, object for comparative     |
| `fault_points`            | int[]  | Write indices where faults were injected            |
| `include_metadata_faults` | bool   | Whether faults were injected during metadata writes |
| `evaluation_mode`         | string | `execute` or `state`                                |
| `control_enabled`         | bool   | Whether control points were included                |
| `summary`                 | object | Per-scenario aggregate counts (see below)           |
| `inputs`                  | object | Platform, firmware, and tooling paths               |
| `execution`               | object | Timestamp, command, artifacts directory             |
| `git`                     | object | Commit hash, short hash, dirty flag                 |
| `results`                 | object | Per-scenario arrays of `FaultResult` entries        |
| `comparative_table`       | string | Rendered text table (comparative scenario only)     |

## `summary.<scenario>`

| Field        | Type  | Description                              |
| ------------ | ----- | ---------------------------------------- |
| `total`      | int   | Number of fault points tested            |
| `bricks`     | int   | Count of `hard_fault` or `hang` outcomes |
| `recoveries` | int   | Count of `success` outcomes              |
| `brick_rate` | float | `bricks / total`                         |

When controls are enabled, `summary.control` contains the unfaulted baseline
outcome for each scenario.

## `results.<scenario>[]` (FaultResult)

| Field          | Type           | Description                                      |
| -------------- | -------------- | ------------------------------------------------ |
| `fault_at`     | int            | Write index where fault was injected             |
| `boot_outcome` | string         | One of: `success`, `hard_fault`, `hang`, `error` |
| `boot_slot`    | string or null | `"A"`, `"B"`, or `null` if no valid slot         |
| `nvm_state`    | object         | Scenario-specific NVM state snapshot             |
| `raw_log`      | string         | Truncated renode-test output (paths redacted)    |
| `is_control`   | bool           | `true` for unfaulted control points              |

### `nvm_state` for vulnerable scenario

| Field                  | Type       | Description                                                    |
| ---------------------- | ---------- | -------------------------------------------------------------- |
| `copy_marker`          | hex string | Value at persistence region; `0xC0FEBEEF` = copy complete      |
| `boot_counter`         | int        | Incremented each copy attempt                                  |
| `pre_boot_counter`     | int        | Counter value before execute-mode run                          |
| `boot_progress`        | bool       | `true` when boot counter changed during execute-mode run       |
| `second_boot_progress` | bool       | `true` when image also booted after a follow-up reset          |
| `evaluation_mode`      | string     | `execute` or `state`                                           |
| `vector_sp`            | hex string | Stack pointer from vector table word 0                         |
| `vector_reset`         | hex string | Reset vector from vector table word 1                          |
| `vector_valid`         | bool       | SP in SRAM range and reset vector in slot range with thumb bit |
| `fault_injected`       | bool       | Whether `InjectPartialWrite` fired                             |

### `nvm_state` for resilient scenario

| Field                     | Type       | Description                                           |
| ------------------------- | ---------- | ----------------------------------------------------- |
| `chosen_slot`             | int        | Slot the bootloader would jump to (0=A, 1=B, -1=none) |
| `requested_slot`          | int        | Slot requested by metadata                            |
| `evaluation_mode`         | string     | `execute` or `state`                                  |
| `write_index`             | int        | How many writes completed before fault                |
| `faulted`                 | bool       | Whether `InjectPartialWrite` fired                    |
| `fault_address`           | hex string | Bus address of the faulted write                      |
| `include_metadata_faults` | bool       | Whether metadata writes were faultable                |
| `replica0_valid`          | bool       | CRC check result for metadata replica 0               |
| `replica1_valid`          | bool       | CRC check result for metadata replica 1               |
| `replica0_seq`            | int        | Sequence number from replica 0                        |
| `replica1_seq`            | int        | Sequence number from replica 1                        |

## Outcome taxonomy

- **`success`**: Firmware boots from a valid slot. The bootloader found a slot
  with a valid vector table (SP in SRAM, reset vector in slot range with thumb bit set).
- **`hard_fault`**: No valid slot exists. Vector table corrupted, no fallback available.
  Device is bricked.
- **`hang`**: CPU stalled without reaching a boot outcome. Detected by timeout in the
  test harness.
- **`error`**: Test infrastructure failure (renode-test crash, missing files). Not a
  firmware outcome.

## Example

See `example_report.json` for a complete comparative campaign with 8 fault points.
The vulnerable scenario bricks on 7/8 fault points (87.5% brick rate).
The resilient scenario recovers from all 8 (0% brick rate).
