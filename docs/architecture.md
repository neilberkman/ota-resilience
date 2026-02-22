# Architecture

## MRAM memory layout

The platform maps a single 512 KB MRAM backing store at three bus addresses:

```mermaid
block-beta
    columns 1
    block:mram["MRAM (0x10000000 -- 0x1007FFFF, 512 KB)"]
        columns 5
        A["Slot A\n0x10002000\n216 KB"] B["Staging/Slot B\n0x10038000\n224 KB"] META["Metadata\n0x10070000\n2 × 256 B"] PERSIST["Persistence\n0x10070200+"] PAD["Reserved"]
    end
```

| Region           | Address range              | Size         | Purpose                                                  |
| ---------------- | -------------------------- | ------------ | -------------------------------------------------------- |
| Boot alias       | `0x00000000`               | mirrors MRAM | CPU fetches vectors/code from here at reset              |
| Slot A (active)  | `0x10002000 -- 0x10037FFF` | 216 KB       | Active firmware image                                    |
| Staging / Slot B | `0x10038000 -- 0x1006FFFF` | 224 KB       | Download/staging area (vulnerable) or slot B (resilient) |
| Boot metadata    | `0x10070000 -- 0x100701FF` | 512 B        | Two 256-byte CRC-protected replicas                      |
| Persistence      | `0x10070200+`              | remainder    | Boot counters, copy markers                              |
| NV read alias    | `0x10080000`               | mirrors MRAM | Read-only mirror; writes silently dropped                |
| Controller regs  | `0x40001000`               | 0x28         | STATUS, CONFIG, CONTROL, ECC counters                    |

The boot alias at `0x00000000` means the Cortex-M0+ vector table fetch
reads directly from MRAM. Corrupting the first 8 bytes of the active slot
is equivalent to bricking the device.

## Vulnerable copy-based OTA flow

The vulnerable firmware (`examples/vulnerable_ota/firmware.c`) copies a
staged image word-by-word from `0x10038000` into the active slot at
`0x10000000`. A power loss at any point during the copy leaves a partially
written vector table and the device will not boot.

```mermaid
flowchart TD
    A[Reset] --> B[Copy staging -> active slot]
    B --> C{Power loss during copy?}
    C -- No --> D[Write completion marker 0xC0FEBEEF]
    D --> E[Boot from active slot]
    C -- Yes --> F[Partial write: vector table corrupted]
    F --> G[hard_fault -- device bricked]

    style G fill:#d32f2f,color:#fff
    style E fill:#388e3c,color:#fff
```

The critical vulnerability: there is exactly one copy of the firmware, and
the copy overwrites it in-place. Any interruption leaves no valid image.

## Resilient A/B bootloader flow

The resilient design (`examples/resilient_ota/bootloader.c`) never
overwrites the running image. New firmware is written to the inactive slot,
then metadata is atomically updated to point at the new slot.

```mermaid
flowchart TD
    A[Reset] --> B[Bootloader reads metadata replicas]
    B --> C{Valid metadata found?}
    C -- Yes --> D[Select active_slot from metadata]
    C -- No --> E[Default to slot A]
    D --> F{active_slot vector table valid?}
    E --> F
    F -- Yes --> G[Jump to active slot]
    F -- No --> H{Fallback slot vector table valid?}
    H -- Yes --> I[Jump to fallback slot]
    H -- No --> J[Spin -- both slots corrupt]

    style G fill:#388e3c,color:#fff
    style I fill:#f9a825,color:#000
    style J fill:#d32f2f,color:#fff
```

### OTA update sequence (host-driven)

```mermaid
flowchart TD
    A[Host writes new image to inactive slot B] --> B{Power loss during slot write?}
    B -- Yes --> C[Slot B partially written\nSlot A untouched\nMetadata still points to A]
    C --> D["Boot: slot A (success)"]
    B -- No --> E[Host writes metadata replica 0\nactive_slot = B, seq++]
    E --> F{Power loss during meta write?}
    F -- Yes, replica 0 corrupt --> G[Replica 1 still valid\npoints to slot A]
    G --> D
    F -- No --> H[Host writes metadata replica 1]
    H --> I{Power loss during meta write?}
    I -- Yes, replica 1 corrupt --> J[Replica 0 valid\npoints to slot B]
    J --> K["Boot: slot B (success)"]
    I -- No --> L[Both replicas valid\npoint to slot B]
    L --> K

    style D fill:#388e3c,color:#fff
    style K fill:#388e3c,color:#fff
```

The key invariant: at every possible fault point, at least one valid
(slot + metadata) pair exists. The bootloader tries the requested slot
first, falls back to the other if vectors are invalid.

## Fault injection model

The campaign runner (`scripts/ota_fault_campaign.py`) iterates over
write indices and injects a partial-write fault at each one via the
MRAM controller's `InjectPartialWrite` method. This zeros the upper
half of the 8-byte word being written, simulating a power loss
mid-program cycle.

```mermaid
flowchart LR
    A[Campaign runner] -->|fault_at=N| B[Robot / renode-test]
    B --> C[Load scenario .resc]
    C --> D[Execute writes 0..N-1 normally]
    D --> E["InjectPartialWrite at write N"]
    E --> F[Evaluate boot outcome from MRAM state]
    F --> G[Write per-point JSON result]
    G --> A
```

Outcomes are determined by reading MRAM state (vector table validity,
metadata CRC, slot markers) -- not by log text parsing.
