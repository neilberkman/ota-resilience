# NVM model

`peripherals/NVMemoryController.cs` contains two Renode peripherals:

- `Memory.NVMemory`: persistent non-volatile memory backing store with configurable word write semantics. Supports MRAM, flash, FRAM, and other NVM technologies.
- `NVMemoryController`: register block at `0x40001000` with status/control and fault hooks.

## Implemented semantics

- Backing store persists across peripheral `Reset()` calls.
- Writes are performed in word-sized erase/program cycles (`WordSize`, default 8 bytes).
- Partial writes trigger read-modify-write merge at word granularity.
- Optional write latency per word (`WriteLatencyMicros`).
- Fault helpers:
  - `InjectFault(address, length[, pattern])`
  - `InjectPartialWrite(address)`

## Register window

The controller exposes the spec register window from `0x00` to `0x54`, including:

- `MISC_STATUS` (`0x00`) with modeled operational bits (`PROG_ACTIVE`, `ERASE_ACTIVE`, `ILLEGAL_OPERATION`)
- `NVM_CTRL` (`0x30`) with writable control bits and always-ready status bits
- ECC counters `NVM_EC[0..3]`, `NVM_UE`, and reset register

## NV_READ_OFFSET alias

`platforms/cortex_m0_nvm.repl` maps an alias at `0x10080000` (`nvm_read_alias`) to the same backing store as base NVM.
