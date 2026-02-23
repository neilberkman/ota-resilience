#!/usr/bin/env python3
"""Property-based state-space fuzzer for OTA bootloader testing.

Generates random initial NVM states (metadata replicas + slot contents) and
predicts the correct bootloader behavior for each, providing an oracle that
can be checked against actual Renode execution.

Usage as library::

    from state_fuzzer import generate_scenarios, expected_outcome, serialize_scenario_to_resc_vars

    for scenario in generate_scenarios(count=200, seed=42):
        outcome = expected_outcome(scenario)
        resc_vars = serialize_scenario_to_resc_vars(scenario)
        # ... feed resc_vars into Renode and compare with outcome

Usage as CLI::

    python3 scripts/state_fuzzer.py --count 50 --seed 42 --output /tmp/fuzz_scenarios.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import struct
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants — must match boot_meta.h / bootloader layout
# ---------------------------------------------------------------------------

BOOT_META_MAGIC = 0x4F54414D
BOOT_META_REPLICA_SIZE = 256  # bytes
BOOT_META_WORD_COUNT = BOOT_META_REPLICA_SIZE // 4  # 64 uint32 words

REPLICA_0_ADDR = 0x10070000
REPLICA_1_ADDR = 0x10070100

SLOT_A_BASE = 0x10002000
SLOT_B_BASE = 0x10039000
SLOT_SIZE = 0x38000 - 0x2000  # 224KB - header offset = 0x37000 usable

SRAM_START = 0x20000000
SRAM_END = 0x20020000

# Slot marker address read back after boot to determine which slot ran.
SLOT_MARKER_ADDR = 0x10070220

# Metadata field indices within the 64-word replica.
IDX_MAGIC = 0
IDX_SEQ = 1
IDX_ACTIVE_SLOT = 2
IDX_TARGET_SLOT = 3
IDX_STATE = 4
IDX_BOOT_COUNT = 5
IDX_MAX_BOOT_COUNT = 6
IDX_CRC = 63  # last word

# Boot states (matching firmware enum).
STATE_CONFIRMED = 0
STATE_PENDING_TEST = 1

CRC_POLYNOMIAL = 0xEDB88320


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MetadataState:
    """Describes the logical content of one metadata replica."""

    seq: int
    active_slot: int
    target_slot: int
    state: int  # STATE_CONFIRMED or STATE_PENDING_TEST
    boot_count: int
    max_boot_count: int
    valid: bool  # Whether CRC should be correct.


@dataclass
class SlotState:
    """Describes the vector table / content pattern for one firmware slot."""

    has_valid_vectors: bool
    content_pattern: str  # "valid_app", "zeros", "random", "partial_write"


@dataclass
class FuzzScenario:
    """A complete initial NVM state to present to the bootloader."""

    replica0: Optional[MetadataState]
    replica1: Optional[MetadataState]
    slot_a: SlotState
    slot_b: SlotState
    fault_at: Optional[int]  # Reserved for combined fuzz+fault tests.
    description: str


@dataclass
class BootOutcome:
    """Predicted bootloader behavior for a given scenario."""

    boots: bool
    boot_slot: Optional[int]  # 0 = A, 1 = B, None = hard fault
    reason: str


# ---------------------------------------------------------------------------
# CRC-32 (matching boot_meta.h implementation)
# ---------------------------------------------------------------------------

def _crc32_table() -> List[int]:
    """Build a 256-entry CRC lookup table."""
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ (CRC_POLYNOMIAL if (crc & 1) else 0)
        table.append(crc & 0xFFFFFFFF)
    return table


_CRC_TABLE = _crc32_table()


def compute_metadata_crc(words: List[int]) -> int:
    """Compute CRC-32 over metadata words, matching boot_meta.h.

    The CRC covers words[0..62] (all except the last word which stores the
    CRC itself). Uses init=0xFFFFFFFF, polynomial=0xEDB88320, final inversion.

    Args:
        words: Full 64-element list of uint32 metadata words.

    Returns:
        The CRC-32 value that should be stored in words[63].
    """
    crc = 0xFFFFFFFF
    for w in words[:-1]:
        for shift in (0, 8, 16, 24):
            byte = (w >> shift) & 0xFF
            crc = _CRC_TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
            crc &= 0xFFFFFFFF
    return (~crc) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Blob builders
# ---------------------------------------------------------------------------

def build_metadata_blob(meta_state: Optional[MetadataState]) -> bytes:
    """Serialize a MetadataState into a 256-byte packed replica.

    If meta_state is None, returns 256 zero bytes (erased / unprogrammed).
    If meta_state.valid is True, the CRC is computed correctly.
    If meta_state.valid is False, the CRC is deliberately corrupted.

    Args:
        meta_state: The metadata to serialize, or None for all-zeros.

    Returns:
        256 bytes of packed little-endian metadata.
    """
    if meta_state is None:
        return b'\x00' * BOOT_META_REPLICA_SIZE

    words = [0] * BOOT_META_WORD_COUNT
    words[IDX_MAGIC] = BOOT_META_MAGIC
    words[IDX_SEQ] = meta_state.seq & 0xFFFFFFFF
    words[IDX_ACTIVE_SLOT] = meta_state.active_slot & 0xFFFFFFFF
    words[IDX_TARGET_SLOT] = meta_state.target_slot & 0xFFFFFFFF
    words[IDX_STATE] = meta_state.state & 0xFFFFFFFF
    words[IDX_BOOT_COUNT] = meta_state.boot_count & 0xFFFFFFFF
    words[IDX_MAX_BOOT_COUNT] = meta_state.max_boot_count & 0xFFFFFFFF

    crc = compute_metadata_crc(words)

    if meta_state.valid:
        words[IDX_CRC] = crc
    else:
        # Corrupt the CRC by flipping bits.
        words[IDX_CRC] = crc ^ 0xDEADBEEF

    return struct.pack('<{}I'.format(BOOT_META_WORD_COUNT), *words)


def build_slot_vectors(slot_state: SlotState, slot_base: int) -> bytes:
    """Build the first 8 bytes (SP + reset_vector) for a firmware slot.

    Args:
        slot_state: Describes what kind of vector table to generate.
        slot_base: The NVM base address of this slot (e.g. 0x10002000).

    Returns:
        8 bytes: [SP (4 bytes LE), reset_vector (4 bytes LE)].
    """
    if slot_state.content_pattern == "zeros":
        return b'\x00' * 8

    if slot_state.content_pattern == "random":
        return bytes(random.getrandbits(8) for _ in range(8))

    if slot_state.content_pattern == "partial_write":
        # Simulate an interrupted 8-byte write: first 4 bytes are valid SP,
        # second 4 bytes are 0xFF (erased NVM default in a partial scenario).
        if slot_state.has_valid_vectors:
            sp = SRAM_START + 0x1000
            return struct.pack('<I', sp) + b'\xFF\xFF\xFF\xFF'
        return b'\xFF' * 8

    # "valid_app" or fallback
    if slot_state.has_valid_vectors:
        sp = SRAM_START + 0x1000  # Plausible stack pointer in SRAM.
        reset_pc = slot_base + 0x100  # Some offset into the slot.
        reset_vector = reset_pc | 1  # Thumb bit set.
        return struct.pack('<II', sp, reset_vector)
    else:
        # Invalid vectors: SP out of SRAM range, no thumb bit.
        sp = 0x00000000
        reset_vector = 0x00000000
        return struct.pack('<II', sp, reset_vector)


# ---------------------------------------------------------------------------
# Sequence number comparison (matching bootloader logic)
# ---------------------------------------------------------------------------

def _seq_ge(a: int, b: int) -> bool:
    """Wrapping sequence comparison: True if a >= b in modular arithmetic."""
    return ((a - b) & 0xFFFFFFFF) < 0x80000000


# ---------------------------------------------------------------------------
# Slot vector validation (matching bootloader logic)
# ---------------------------------------------------------------------------

def _slot_base_for_id(slot_id: int) -> int:
    """Return the NVM base address for a given slot ID."""
    return SLOT_B_BASE if slot_id == 1 else SLOT_A_BASE


def _vectors_valid_from_state(slot_state: SlotState, slot_base: int) -> bool:
    """Predict whether the bootloader would consider this slot's vectors valid.

    Reconstructs the same check the bootloader performs:
    - SP in [0x20000000, 0x20020000]
    - reset_vector has thumb bit set
    - reset_pc (without thumb bit) falls within the slot range
    """
    vec_bytes = build_slot_vectors(slot_state, slot_base)
    sp, reset_vector = struct.unpack('<II', vec_bytes)
    reset_pc = reset_vector & ~1

    return (
        (SRAM_START <= sp <= SRAM_END)
        and ((reset_vector & 1) == 1)
        and (slot_base <= reset_pc < (slot_base + 0x37000))
    )


# ---------------------------------------------------------------------------
# Oracle: expected_outcome
# ---------------------------------------------------------------------------

def expected_outcome(scenario: FuzzScenario) -> BootOutcome:
    """Predict the correct bootloader behavior for a given scenario.

    Implements the same decision logic as the resilient bootloader:
    1. Read both metadata replicas.
    2. Select the highest-seq valid replica (wrapping comparison).
    3. Try to boot the active_slot from the selected replica.
    4. If that slot has invalid vectors, fall back to the other slot.
    5. If both slots have invalid vectors, hard fault.
    6. If no valid replica exists, default to slot A.

    Args:
        scenario: The full NVM initial state.

    Returns:
        A BootOutcome describing the predicted boot result.
    """
    # Determine which replica is selected.
    r0_valid = (scenario.replica0 is not None) and scenario.replica0.valid
    r1_valid = (scenario.replica1 is not None) and scenario.replica1.valid

    selected: Optional[MetadataState] = None
    selection_reason = ""

    if r0_valid and r1_valid:
        assert scenario.replica0 is not None
        assert scenario.replica1 is not None
        if _seq_ge(scenario.replica0.seq, scenario.replica1.seq):
            selected = scenario.replica0
            selection_reason = "replica0 wins (seq {} >= {})".format(
                scenario.replica0.seq, scenario.replica1.seq
            )
        else:
            selected = scenario.replica1
            selection_reason = "replica1 wins (seq {} > {})".format(
                scenario.replica1.seq, scenario.replica0.seq
            )
    elif r0_valid:
        selected = scenario.replica0
        selection_reason = "only replica0 valid"
    elif r1_valid:
        selected = scenario.replica1
        selection_reason = "only replica1 valid"
    else:
        selection_reason = "no valid replica, defaulting to slot A"

    # Determine requested slot, accounting for PENDING_TEST revert.
    if selected is not None:
        requested_slot = selected.active_slot

        # If in PENDING_TEST state and boot_count >= max_boot_count,
        # the bootloader reverts to the alternate slot.
        if selected.state == STATE_PENDING_TEST:
            effective_max = selected.max_boot_count if selected.max_boot_count > 0 else 3
            if selected.boot_count >= effective_max:
                # Revert: switch to the other slot and mark confirmed.
                if requested_slot == 0:
                    requested_slot = 1
                elif requested_slot == 1:
                    requested_slot = 0
                else:
                    requested_slot = 0  # Invalid slot ID -> slot_base_for_id returns A
                selection_reason += "; PENDING_TEST exhausted (boot_count={} >= max={}), reverted".format(
                    selected.boot_count, effective_max
                )
    else:
        requested_slot = 0  # Default to slot A.

    # Determine slot validity.
    slot_a_valid = _vectors_valid_from_state(scenario.slot_a, SLOT_A_BASE)
    slot_b_valid = _vectors_valid_from_state(scenario.slot_b, SLOT_B_BASE)

    # Bootloader slot selection with fallback.
    if requested_slot == 0:
        if slot_a_valid:
            return BootOutcome(
                boots=True,
                boot_slot=0,
                reason="{}; slot A vectors valid".format(selection_reason),
            )
        elif slot_b_valid:
            return BootOutcome(
                boots=True,
                boot_slot=1,
                reason="{}; slot A invalid, fell back to slot B".format(selection_reason),
            )
        else:
            return BootOutcome(
                boots=False,
                boot_slot=None,
                reason="{}; both slots have invalid vectors".format(selection_reason),
            )
    elif requested_slot == 1:
        if slot_b_valid:
            return BootOutcome(
                boots=True,
                boot_slot=1,
                reason="{}; slot B vectors valid".format(selection_reason),
            )
        elif slot_a_valid:
            return BootOutcome(
                boots=True,
                boot_slot=0,
                reason="{}; slot B invalid, fell back to slot A".format(selection_reason),
            )
        else:
            return BootOutcome(
                boots=False,
                boot_slot=None,
                reason="{}; both slots have invalid vectors".format(selection_reason),
            )
    else:
        # Nonexistent slot ID — bootloader treats as invalid, falls back.
        if slot_a_valid:
            return BootOutcome(
                boots=True,
                boot_slot=0,
                reason="{}; invalid slot id {}, fell back to slot A".format(
                    selection_reason, requested_slot
                ),
            )
        elif slot_b_valid:
            return BootOutcome(
                boots=True,
                boot_slot=1,
                reason="{}; invalid slot id {}, fell back to slot B".format(
                    selection_reason, requested_slot
                ),
            )
        else:
            return BootOutcome(
                boots=False,
                boot_slot=None,
                reason="{}; invalid slot id {}, both slots invalid".format(
                    selection_reason, requested_slot
                ),
            )


# ---------------------------------------------------------------------------
# Renode injection serialization
# ---------------------------------------------------------------------------

def serialize_scenario_to_resc_vars(scenario: FuzzScenario) -> Dict[str, Any]:
    """Convert a FuzzScenario to WriteDoubleWord calls for Renode injection.

    Returns a dict with:
    - "writes": list of (address, value) tuples for bus.WriteDoubleWord
    - "description": human-readable scenario description
    - "fault_at": optional fault injection point

    The caller is responsible for iterating the writes list and issuing
    ``bus.WriteDoubleWord(addr, value)`` in the Renode Python monitor.

    Args:
        scenario: The scenario to serialize.

    Returns:
        Dict with injection data.
    """
    writes: List[Tuple[int, int]] = []

    # Write replica 0.
    r0_blob = build_metadata_blob(scenario.replica0)
    for i in range(0, BOOT_META_REPLICA_SIZE, 4):
        word = struct.unpack_from('<I', r0_blob, i)[0]
        writes.append((REPLICA_0_ADDR + i, word))

    # Write replica 1.
    r1_blob = build_metadata_blob(scenario.replica1)
    for i in range(0, BOOT_META_REPLICA_SIZE, 4):
        word = struct.unpack_from('<I', r1_blob, i)[0]
        writes.append((REPLICA_1_ADDR + i, word))

    # Write slot A vectors (first 8 bytes).
    slot_a_vec = build_slot_vectors(scenario.slot_a, SLOT_A_BASE)
    for i in range(0, 8, 4):
        word = struct.unpack_from('<I', slot_a_vec, i)[0]
        writes.append((SLOT_A_BASE + i, word))

    # Write slot B vectors (first 8 bytes).
    slot_b_vec = build_slot_vectors(scenario.slot_b, SLOT_B_BASE)
    for i in range(0, 8, 4):
        word = struct.unpack_from('<I', slot_b_vec, i)[0]
        writes.append((SLOT_B_BASE + i, word))

    return {
        "writes": writes,
        "description": scenario.description,
        "fault_at": scenario.fault_at,
    }


# ---------------------------------------------------------------------------
# Scenario generators
# ---------------------------------------------------------------------------

def _random_metadata(rng: random.Random, *, force_valid: Optional[bool] = None) -> MetadataState:
    """Generate a random MetadataState."""
    valid = force_valid if force_valid is not None else rng.choice([True, False])
    return MetadataState(
        seq=rng.randint(0, 0xFFFFFFFF),
        active_slot=rng.choice([0, 1]),
        target_slot=rng.choice([0, 1]),
        state=rng.choice([STATE_CONFIRMED, STATE_PENDING_TEST]),
        boot_count=rng.randint(0, 10),
        max_boot_count=rng.randint(1, 5),
        valid=valid,
    )


def _random_slot(rng: random.Random, *, force_valid: Optional[bool] = None) -> SlotState:
    """Generate a random SlotState."""
    if force_valid is True:
        return SlotState(has_valid_vectors=True, content_pattern="valid_app")
    if force_valid is False:
        return SlotState(
            has_valid_vectors=False,
            content_pattern=rng.choice(["zeros", "random", "partial_write"]),
        )
    has_valid = rng.choice([True, False])
    pattern = rng.choice(["valid_app", "zeros", "random", "partial_write"])
    # If pattern is valid_app, vectors should be valid for it to make sense.
    if pattern == "valid_app":
        has_valid = True
    return SlotState(has_valid_vectors=has_valid, content_pattern=pattern)


def generate_scenarios(count: int = 100, seed: Optional[int] = None) -> List[FuzzScenario]:
    """Generate a suite of random FuzzScenarios for bootloader testing.

    The generator produces a mix of targeted edge cases and purely random
    scenarios to maximize state-space coverage.

    Args:
        count: Total number of scenarios to generate.
        seed: Optional RNG seed for reproducibility.

    Returns:
        List of FuzzScenario instances.
    """
    rng = random.Random(seed)
    scenarios: List[FuzzScenario] = []

    # --- Targeted edge cases (always included) ---

    # 1. Both replicas valid, different seq numbers — replica0 wins.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=5, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=3, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="both replicas valid, replica0 higher seq -> slot A",
    ))

    # 2. Both replicas valid, different seq numbers — replica1 wins.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=2, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=7, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="both replicas valid, replica1 higher seq -> slot B",
    ))

    # 3. One valid, one corrupt — valid one selects slot B.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=10, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=False),
        replica1=MetadataState(seq=8, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="replica0 corrupt, replica1 valid -> slot B",
    ))

    # 4. Both replicas corrupt — should default to slot A.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=1, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=False),
        replica1=MetadataState(seq=2, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=False),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="both replicas corrupt -> default slot A",
    ))

    # 5. Both replicas corrupt, slot A also invalid -> hard fault.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=1, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=False),
        replica1=MetadataState(seq=1, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=False),
        slot_a=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="both replicas corrupt, default slot A invalid -> fall back to slot B",
    ))

    # 6. Metadata points to slot with invalid vectors -> fallback.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=5, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=None,
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        fault_at=None,
        description="metadata says slot B but slot B invalid -> fall back to A",
    ))

    # 7. Both slots invalid -> hard fault regardless of metadata.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=1, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=None,
        slot_a=SlotState(has_valid_vectors=False, content_pattern="random"),
        slot_b=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        fault_at=None,
        description="both slots have invalid vectors -> hard fault",
    ))

    # 8. Seq number wrapping: 0xFFFFFFFF vs 0x00000001.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=0xFFFFFFFF, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=0x00000001, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="seq wrapping: 0xFFFFFFFF vs 0x00000001 -> replica1 wins (wrapped ahead)",
    ))

    # 9. Seq number wrapping: 0x80000000 boundary.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=0x80000000, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=0x00000001, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="seq boundary: 0x80000000 vs 0x00000001 -> replica0 wins (within half-range)",
    ))

    # 10. Nonexistent slot ID in metadata.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=5, active_slot=99, target_slot=99,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=None,
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="nonexistent slot id 99 -> fall back to slot A",
    ))

    # 11. All-zero metadata region (erased NVM).
    scenarios.append(FuzzScenario(
        replica0=None,
        replica1=None,
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        fault_at=None,
        description="all-zero metadata (erased NVM) -> default slot A",
    ))

    # 12. Partially-written metadata (simulating interrupted update).
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=3, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=4, active_slot=1, target_slot=1,
                               state=STATE_PENDING_TEST, boot_count=0,
                               max_boot_count=3, valid=False),  # Interrupted write = bad CRC
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="interrupted metadata update: replica1 corrupt -> replica0 wins -> slot A",
    ))

    # 13. Pending test with exhausted boot count.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=10, active_slot=1, target_slot=1,
                               state=STATE_PENDING_TEST, boot_count=3,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=9, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="pending_test with exhausted boot_count -> slot B (bootloader reads active_slot)",
    ))

    # 14. Slot A partial write, slot B valid.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=1, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=None,
        slot_a=SlotState(has_valid_vectors=False, content_pattern="partial_write"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="slot A partial write -> fall back to slot B",
    ))

    # 15. Equal seq numbers, both valid.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=5, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=5, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="equal seq -> replica0 wins (seq_ge tie-break) -> slot A",
    ))

    # 16. Maximum slot ID value.
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=1, active_slot=0xFFFFFFFF, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=None,
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        fault_at=None,
        description="max uint32 slot id -> fall back to slot A",
    ))

    # 17. Seq=0 in one replica (could confuse naive zero-check logic).
    scenarios.append(FuzzScenario(
        replica0=MetadataState(seq=0, active_slot=0, target_slot=0,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        replica1=MetadataState(seq=1, active_slot=1, target_slot=1,
                               state=STATE_CONFIRMED, boot_count=0,
                               max_boot_count=3, valid=True),
        slot_a=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        slot_b=SlotState(has_valid_vectors=True, content_pattern="valid_app"),
        fault_at=None,
        description="seq=0 vs seq=1 -> replica1 wins -> slot B",
    ))

    # 18. Both replicas None, both slots invalid -> total failure.
    scenarios.append(FuzzScenario(
        replica0=None,
        replica1=None,
        slot_a=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        slot_b=SlotState(has_valid_vectors=False, content_pattern="zeros"),
        fault_at=None,
        description="totally blank NVM -> hard fault",
    ))

    targeted_count = len(scenarios)

    # --- Random scenarios to fill the rest ---
    remaining = max(0, count - targeted_count)

    for i in range(remaining):
        # Choose a random scenario shape.
        shape = rng.choice([
            "both_valid",
            "one_valid",
            "both_corrupt",
            "one_none",
            "both_none",
            "invalid_slot_id",
            "seq_boundary",
            "fully_random",
        ])

        if shape == "both_valid":
            r0 = _random_metadata(rng, force_valid=True)
            r1 = _random_metadata(rng, force_valid=True)
            desc = "random: both replicas valid (seq {}:{})".format(r0.seq, r1.seq)

        elif shape == "one_valid":
            if rng.choice([True, False]):
                r0 = _random_metadata(rng, force_valid=True)
                r1 = _random_metadata(rng, force_valid=False) if rng.choice([True, False]) else None
                desc = "random: replica0 valid, replica1 {}".format(
                    "corrupt" if r1 is not None else "absent"
                )
            else:
                r0 = _random_metadata(rng, force_valid=False) if rng.choice([True, False]) else None
                r1 = _random_metadata(rng, force_valid=True)
                desc = "random: replica0 {}, replica1 valid".format(
                    "corrupt" if r0 is not None else "absent"
                )

        elif shape == "both_corrupt":
            r0 = _random_metadata(rng, force_valid=False)
            r1 = _random_metadata(rng, force_valid=False)
            desc = "random: both replicas corrupt"

        elif shape == "one_none":
            if rng.choice([True, False]):
                r0 = _random_metadata(rng)
                r1 = None
                desc = "random: replica0 present (valid={}), replica1 absent".format(r0.valid)
            else:
                r0 = None
                r1 = _random_metadata(rng)
                desc = "random: replica0 absent, replica1 present (valid={})".format(r1.valid)

        elif shape == "both_none":
            r0 = None
            r1 = None
            desc = "random: both replicas absent (erased NVM)"

        elif shape == "invalid_slot_id":
            r0 = _random_metadata(rng, force_valid=True)
            r0.active_slot = rng.choice([2, 3, 99, 255, 0xFFFFFFFF, rng.randint(2, 0xFFFFFFFE)])
            r1 = _random_metadata(rng) if rng.choice([True, False]) else None
            desc = "random: invalid slot id {} in replica0".format(r0.active_slot)

        elif shape == "seq_boundary":
            r0 = _random_metadata(rng, force_valid=True)
            r1 = _random_metadata(rng, force_valid=True)
            # Force interesting seq values near wrapping boundaries.
            boundary = rng.choice([
                (0xFFFFFFFF, 0x00000000),
                (0xFFFFFFFF, 0x00000001),
                (0x7FFFFFFF, 0x80000000),
                (0x80000000, 0x7FFFFFFF),
                (0x00000000, 0xFFFFFFFF),
                (0xFFFFFFFE, 0xFFFFFFFF),
            ])
            r0.seq, r1.seq = boundary
            desc = "random: seq boundary test ({:#x} vs {:#x})".format(r0.seq, r1.seq)

        else:  # fully_random
            r0 = _random_metadata(rng) if rng.choice([True, False]) else None
            r1 = _random_metadata(rng) if rng.choice([True, False]) else None
            desc = "random: fully random scenario #{}".format(i)

        slot_a = _random_slot(rng)
        slot_b = _random_slot(rng)

        scenarios.append(FuzzScenario(
            replica0=r0,
            replica1=r1,
            slot_a=slot_a,
            slot_b=slot_b,
            fault_at=None,
            description=desc,
        ))

    return scenarios[:count]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _scenario_to_dict(scenario: FuzzScenario) -> Dict[str, Any]:
    """Convert a scenario + its expected outcome to a JSON-serializable dict."""
    outcome = expected_outcome(scenario)
    resc = serialize_scenario_to_resc_vars(scenario)

    return {
        "description": scenario.description,
        "expected": {
            "boots": outcome.boots,
            "boot_slot": outcome.boot_slot,
            "reason": outcome.reason,
        },
        "replica0": dataclasses.asdict(scenario.replica0) if scenario.replica0 else None,
        "replica1": dataclasses.asdict(scenario.replica1) if scenario.replica1 else None,
        "slot_a": dataclasses.asdict(scenario.slot_a),
        "slot_b": dataclasses.asdict(scenario.slot_b),
        "fault_at": scenario.fault_at,
        "write_count": len(resc["writes"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate OTA bootloader state-space fuzz scenarios."
    )
    parser.add_argument(
        "--count", type=int, default=100,
        help="Number of scenarios to generate (default: 100).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for reproducibility.",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON file path. Defaults to stdout.",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print a summary of expected outcomes to stderr.",
    )
    args = parser.parse_args()

    scenarios = generate_scenarios(count=args.count, seed=args.seed)
    payload = [_scenario_to_dict(s) for s in scenarios]

    json_text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_text)
            f.write('\n')
        print("Wrote {} scenarios to {}".format(len(scenarios), args.output),
              file=sys.stderr)
    else:
        print(json_text)

    if args.summary:
        boots_count = sum(1 for s in scenarios if expected_outcome(s).boots)
        fault_count = sum(1 for s in scenarios if not expected_outcome(s).boots)
        slot_a = sum(1 for s in scenarios
                     if expected_outcome(s).boots and expected_outcome(s).boot_slot == 0)
        slot_b = sum(1 for s in scenarios
                     if expected_outcome(s).boots and expected_outcome(s).boot_slot == 1)
        print("", file=sys.stderr)
        print("Summary ({} scenarios):".format(len(scenarios)), file=sys.stderr)
        print("  Boots successfully: {} ({:.1f}%)".format(
            boots_count, 100.0 * boots_count / len(scenarios) if scenarios else 0
        ), file=sys.stderr)
        print("    -> Slot A: {}".format(slot_a), file=sys.stderr)
        print("    -> Slot B: {}".format(slot_b), file=sys.stderr)
        print("  Hard fault: {} ({:.1f}%)".format(
            fault_count, 100.0 * fault_count / len(scenarios) if scenarios else 0
        ), file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
