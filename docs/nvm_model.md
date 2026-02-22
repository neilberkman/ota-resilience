# NVM model

`peripherals/NVMemoryController.cs` contains two Renode peripherals:

- `Memory.LocalNVMemory`: persistent NVM backing store with configurable write/erase semantics.
- `NVMemoryController`: register block at `0x40001000` with status/control and fault hooks.

## Implemented semantics

- Backing store persists across peripheral `Reset()` calls.
- Writes are performed in word-sized cycles (`WordSize`), default 8 bytes.
- Erased bytes default to `0xFF` (`EraseFill`).
- Optional sector model (`SectorSize`) with explicit sector erase APIs.
- Optional flash-style write enforcement (`EnforceEraseBeforeWrite`) that rejects `0 -> 1` bit transitions without erase.
- Partial writes are word-granularity and respect configured semantics.
- Fault helpers:
  - `InjectFault(address, length[, pattern])`
  - `InjectPartialWrite(address)`
  - `EraseSector(address)`
  - `InjectPartialErase(address)`

## Runtime configuration

`NVMemoryController` exposes runtime properties used from platform `.repl` files:

- `WriteGranularity` (`WordSize` in `LocalNVMemory`), default `8`
- `SectorSize`, default `0` (disabled)
- `EraseValue` (`EraseFill` in `LocalNVMemory`), default `0xFF`
- `EnforceEraseBeforeWrite`, default `false`

The built-in profiles are:

- `platforms/cortex_m0_nvm.repl`: MRAM-like defaults (`WriteGranularity=8`, `SectorSize=0`)
- `platforms/cortex_m4_flash.repl`: flash-like defaults (`WriteGranularity=256`, `SectorSize=4096`, erase-before-write enabled)

## Register map

The controller exposes registers from `0x00` to `0x34`:

| Offset | Register                    | Access | Purpose                                              |
| ------ | --------------------------- | ------ | ---------------------------------------------------- |
| `0x00` | `STATUS`                    | RO     | Ready, write-in-progress, fault latch, last error    |
| `0x04` | `CONFIGURATION`             | RW     | `FULL_MODE`, `ENFORCE_WORD_WRITES`                   |
| `0x08` | `NVM_BASE_ADDRESS`         | RW     | Absolute base used for address normalization         |
| `0x0C` | `NV_READ_OFFSET`            | RW     | Offset from NVM base to read-only alias             |
| `0x10` | `CONTROL`                   | RW     | Program/erase enables, ready override, clear/reset   |
| `0x14` | `FAULT_ADDRESS`             | RW     | Target address for command-triggered fault injection |
| `0x18` | `FAULT_LENGTH`              | RW     | Length for region corruption command                 |
| `0x1C` | `FAULT_PATTERN`             | RW     | Byte pattern for region corruption                   |
| `0x20` | `COMMAND`                   | WO     | Trigger partial-write or region fault                |
| `0x24` | `WORD_WRITE_COUNT_LO`       | RO     | Low 32 bits of NVM word-write counter               |
| `0x28` | `WORD_WRITE_COUNT_HI`       | RO     | High 32 bits of NVM word-write counter              |
| `0x2C` | `PARTIAL_WRITE_FAULT_COUNT` | RO     | Number of partial-write injections                   |
| `0x30` | `REGION_FAULT_COUNT`        | RO     | Number of region-fault injections                    |
| `0x34` | `ERROR_COUNT`               | RO     | Number of controller-level errors                    |

## NV read alias

`platforms/cortex_m0_nvm.repl` maps `NVReadOnlyAlias` at `0x10080000` to the
same backing store as base NVM. Reads are forwarded transparently; writes are
silently dropped. This models cache-bypass read ports found on some NVM
controllers.

## Addressing rules

`NVMemoryController` accepts fault addresses in any of these forms:

- NVM-relative offset (`0x0..0x7FFFF`)
- Absolute NVM address (`0x10000000..0x1007FFFF`)
- Absolute NV read-alias address (`0x10080000..0x100FFFFF`)

The controller normalizes all of them to NVM-relative offsets before delegating
to `LocalNVMemory`.
