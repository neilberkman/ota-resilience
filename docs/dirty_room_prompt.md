# Dirty Room Agent Prompt Template

Use this prompt to instruct a separate agent (with access to proprietary firmware)
how to use the ota-resilience tool against your specific bootloader. This agent
should be sandboxed — it MUST NOT contribute code back to the ota-resilience repo.

---

## Prompt

You have access to a proprietary firmware codebase. Your task is to configure the
ota-resilience toolkit to audit this firmware's bootloader for power-loss safety.

### What you need to produce

1. **A Renode platform description (.repl)** matching your target's memory map:
   - NVM base address and size
   - NVM word size (write granularity)
   - SRAM base and size
   - Any memory-mapped peripherals the bootloader touches during boot

2. **Slot geometry parameters** for the audit tool:
   - `SLOT_A_BASE` / `SLOT_A_SIZE` — primary firmware slot address and size
   - `SLOT_B_BASE` / `SLOT_B_SIZE` — staging/download/alternate slot
   - `META_BASE_0` / `META_BASE_1` — boot metadata locations (if applicable)
   - `META_SIZE` — metadata replica size

3. **A bootloader ELF** built for the target (debug-stripped, no proprietary paths).

4. **Slot images** (optional but recommended):
   - A known-good firmware image for slot A
   - A known-good firmware image for slot B
   - These exercise the "both slots valid" and "fallback" code paths

5. **Any required C# peripheral stubs** for Renode (register stubs for
   peripherals the bootloader reads during init).

### How to run the audit

```bash
python3 scripts/audit_bootloader.py \
    --bootloader-elf /path/to/your/bootloader.elf \
    --platform /path/to/your/platform.repl \
    --slot-a-image /path/to/slot_a.bin \
    --slot-b-image /path/to/slot_b.bin \
    --peripheral-includes "/path/to/stub1.cs;/path/to/stub2.cs" \
    --robot-var "SLOT_A_BASE:0xNNNNNNNN" \
    --robot-var "SLOT_B_BASE:0xNNNNNNNN" \
    --robot-var "SLOT_SIZE:0xNNNN" \
    --robot-var "META_BASE_0:0xNNNNNNNN" \
    --robot-var "META_BASE_1:0xNNNNNNNN" \
    --robot-var "META_SIZE:256" \
    --robot-var "BOOTLOADER_ENTRY:0xNNNNNNNN" \
    --output results/your_firmware_audit.json \
    --workers 4
```

### Interpreting results

The tool generates a JSON report with:

- **verdict**: PASS/WARN/FAIL summary
- **faulted_bricks**: number of fault-injection scenarios that bricked
- **faulted_with_violations**: invariant violations detected
- **interesting_results**: detailed per-scenario data for failures

Key invariants checked:

- `at_least_one_bootable`: if pre-fault state had a valid slot, boot must succeed
- `metadata_single_fault_consistency`: one fault cannot corrupt both metadata replicas
- `boot_matches_metadata`: boot slot matches what metadata requested
- `slot_integrity`: if boot reports success, vector table must be valid
- `no_oob_writes`: no writes outside allowed partition ranges

### Common bootloader patterns and what to configure

**Pattern: Simple copy-to-address (no real bootloader)**

- Only one "slot" — the execution address
- Set `SLOT_A_BASE` to the execution address
- Set `SLOT_B_BASE` to the staging/download address
- Expect HIGH brick rate — this is by design, to show the vulnerability

**Pattern: A/B with metadata**

- Two slots + metadata region
- Set all slot and metadata parameters
- Expect low brick rate if implementation is correct

**Pattern: MCUboot swap**

- Use `--robot-var "OTA_HEADER_SIZE:0x200"` if images have MCUboot headers
- Use geometry_matrix.py to generate the platform description

### What NOT to do

- Do NOT commit proprietary firmware, paths, or peripheral names to the
  ota-resilience repo
- Do NOT push results containing proprietary information to public remotes
- Strip all debug info from ELFs before sharing: `objcopy --strip-debug`
- Audit all file paths in results JSON for proprietary content before sharing
