#!/usr/bin/env python3
"""YAML profile loader for OTA bootloader fault-injection testing.

Parses declarative bootloader profiles, validates against schema_version 1,
and emits robot variables / temp files for the fault-injection harness.

Usage as library::

    from profile_loader import load_profile, ProfileConfig

    profile = load_profile("profiles/naive_bare_copy.yaml")
    robot_vars = profile.robot_vars(repo_root)

Usage as CLI (for debugging)::

    python3 scripts/profile_loader.py profiles/naive_bare_copy.yaml
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


SUPPORTED_SCHEMA_VERSIONS = {1}

KNOWN_FAULT_TYPES = {"power_loss", "interrupted_erase", "write_rejection", "reset_at_time"}
IMPLEMENTED_FAULT_TYPES = {"power_loss"}


class ProfileError(Exception):
    """Raised when a profile is invalid or unsupported."""


# ---------------------------------------------------------------------------
# Profile data model
# ---------------------------------------------------------------------------

class SlotConfig:
    __slots__ = ("base", "size")

    def __init__(self, base: int, size: int) -> None:
        self.base = base
        self.size = size


class MemoryConfig:
    __slots__ = ("sram_start", "sram_end", "write_granularity", "slots")

    def __init__(
        self,
        sram_start: int,
        sram_end: int,
        write_granularity: int,
        slots: Dict[str, SlotConfig],
    ) -> None:
        self.sram_start = sram_start
        self.sram_end = sram_end
        self.write_granularity = write_granularity
        self.slots = slots


class SuccessCriteria:
    __slots__ = ("vtor_in_slot", "pc_in_slot", "marker_address", "marker_value")

    def __init__(
        self,
        vtor_in_slot: Optional[str] = None,
        pc_in_slot: Optional[str] = None,
        marker_address: Optional[int] = None,
        marker_value: Optional[int] = None,
    ) -> None:
        self.vtor_in_slot = vtor_in_slot
        self.pc_in_slot = pc_in_slot
        self.marker_address = marker_address
        self.marker_value = marker_value


class FaultSweepConfig:
    __slots__ = ("mode", "max_writes", "max_writes_cap", "max_step_limit", "run_duration", "fault_types", "evaluation_mode", "sweep_strategy")

    def __init__(
        self,
        mode: str = "runtime",
        max_writes: Any = "auto",
        max_writes_cap: int = 100000,
        max_step_limit: int = 500000,
        run_duration: str = "0.5",
        fault_types: Optional[List[str]] = None,
        evaluation_mode: Optional[str] = None,
        sweep_strategy: str = "heuristic",
    ) -> None:
        self.mode = mode
        self.max_writes = max_writes
        self.max_writes_cap = max_writes_cap
        self.max_step_limit = max_step_limit
        self.run_duration = run_duration
        self.fault_types = fault_types or ["power_loss"]
        self.evaluation_mode = evaluation_mode
        self.sweep_strategy = sweep_strategy


class StateFuzzerConfig:
    __slots__ = ("enabled", "metadata_model")

    def __init__(self, enabled: bool = False, metadata_model: str = "ab_replica") -> None:
        self.enabled = enabled
        self.metadata_model = metadata_model


class ExpectConfig:
    __slots__ = ("should_find_issues", "brick_rate_min")

    def __init__(self, should_find_issues: bool = True, brick_rate_min: float = 0.0) -> None:
        self.should_find_issues = should_find_issues
        self.brick_rate_min = brick_rate_min


class PreBootWrite:
    __slots__ = ("address", "u32")

    def __init__(self, address: int, u32: int) -> None:
        self.address = address
        self.u32 = u32


VALID_SCENARIOS = {"runtime", "resilient", "vulnerable"}


class ProfileConfig:
    """Fully-parsed bootloader profile."""

    def __init__(
        self,
        schema_version: int,
        name: str,
        description: str,
        platform: str,
        bootloader_elf: str,
        bootloader_entry: int,
        memory: MemoryConfig,
        images: Dict[str, str],
        pre_boot_state: List[PreBootWrite],
        setup_script: Optional[str],
        success_criteria: SuccessCriteria,
        fault_sweep: FaultSweepConfig,
        state_fuzzer: StateFuzzerConfig,
        expect: ExpectConfig,
        profile_path: Optional[Path] = None,
        scenario: str = "runtime",
    ) -> None:
        self.schema_version = schema_version
        self.name = name
        self.description = description
        self.platform = platform
        self.bootloader_elf = bootloader_elf
        self.bootloader_entry = bootloader_entry
        self.memory = memory
        self.images = images
        self.pre_boot_state = pre_boot_state
        self.setup_script = setup_script
        self.success_criteria = success_criteria
        self.fault_sweep = fault_sweep
        self.state_fuzzer = state_fuzzer
        self.expect = expect
        self.profile_path = profile_path
        self.scenario = scenario

    def resolve_path(self, repo_root: Path, value: str) -> str:
        """Resolve a path relative to the repo root."""
        p = Path(value)
        if p.is_absolute():
            return str(p)
        return str((repo_root / p).resolve())

    def generate_pre_boot_bin(self) -> Optional[str]:
        """Write pre_boot_state entries to a temp .bin file.

        Returns the temp file path, or None if no pre_boot_state.
        The caller is responsible for cleanup.
        """
        if not self.pre_boot_state:
            return None

        # Format: sequence of (u32 address, u32 value) pairs.
        data = bytearray()
        for write in self.pre_boot_state:
            data.extend(struct.pack("<II", write.address, write.u32))

        tmp = tempfile.NamedTemporaryFile(
            prefix="pre_boot_state_", suffix=".bin", delete=False
        )
        tmp.write(bytes(data))
        tmp.close()
        return tmp.name

    def robot_vars(self, repo_root: Path) -> List[str]:
        """Generate Robot Framework --variable arguments for this profile."""
        mem = self.memory
        sc = self.success_criteria
        fs = self.fault_sweep

        # Classic scenario routing: resilient/vulnerable use legacy robot path.
        if self.scenario == "resilient":
            return self._resilient_robot_vars(repo_root)

        vars_list: List[str] = [
            "PLATFORM_REPL:{}".format(self.resolve_path(repo_root, self.platform)),
            "BOOTLOADER_ELF:{}".format(self.resolve_path(repo_root, self.bootloader_elf)),
            "BOOTLOADER_ENTRY:0x{:08X}".format(self.bootloader_entry),
            "SRAM_START:0x{:08X}".format(mem.sram_start),
            "SRAM_END:0x{:08X}".format(mem.sram_end),
            "WRITE_GRANULARITY:{}".format(mem.write_granularity),
            "RUN_DURATION:{}".format(fs.run_duration),
            "MAX_STEP_LIMIT:{}".format(fs.max_step_limit),
            "MAX_WRITES_CAP:{}".format(fs.max_writes_cap),
            "RUNTIME_MODE:true",
        ]

        # Slot info.
        for slot_name, slot_cfg in mem.slots.items():
            prefix = "SLOT_{}_".format(slot_name.upper())
            vars_list.append("{}BASE:0x{:08X}".format(prefix, slot_cfg.base))
            vars_list.append("{}SIZE:0x{:08X}".format(prefix, slot_cfg.size))

        # Images (robot variables for Load Runtime Scenario + paths for batch reload).
        for img_name, img_path in self.images.items():
            resolved = self.resolve_path(repo_root, img_path)
            vars_list.append("IMAGE_{}:{}".format(img_name.upper(), resolved))
            vars_list.append("IMAGE_{}_PATH:{}".format(img_name.upper(), resolved))

        # Success criteria.
        if sc.vtor_in_slot:
            vars_list.append("SUCCESS_VTOR_SLOT:{}".format(sc.vtor_in_slot))
        else:
            vars_list.append("SUCCESS_VTOR_SLOT:")
        if sc.pc_in_slot:
            vars_list.append("SUCCESS_PC_SLOT:{}".format(sc.pc_in_slot))
        if sc.marker_address is not None:
            vars_list.append("SUCCESS_MARKER_ADDR:0x{:08X}".format(sc.marker_address))
        if sc.marker_value is not None:
            vars_list.append("SUCCESS_MARKER_VALUE:0x{:08X}".format(sc.marker_value))

        # Pre-boot state.
        pre_boot_bin = self.generate_pre_boot_bin()
        if pre_boot_bin:
            vars_list.append("PRE_BOOT_STATE_BIN:{}".format(pre_boot_bin))

        # Setup script.
        if self.setup_script:
            vars_list.append(
                "SETUP_SCRIPT:{}".format(self.resolve_path(repo_root, self.setup_script))
            )

        return vars_list

    def _resilient_robot_vars(self, repo_root: Path) -> List[str]:
        """Generate robot vars for resilient A/B scenario (legacy path)."""
        mem = self.memory
        fs = self.fault_sweep

        include_meta = "true" if self.state_fuzzer.enabled else "false"

        # Compute total writes if not set explicitly.
        total_writes = fs.max_writes
        if total_writes == "auto" and "exec" in mem.slots:
            total_writes = mem.slots["exec"].size // mem.write_granularity

        vars_list: List[str] = [
            "SCENARIO:resilient",
            "RUNTIME_MODE:false",
            "PLATFORM_REPL:{}".format(self.resolve_path(repo_root, self.platform)),
            "RESILIENT_BOOTLOADER_ELF:{}".format(
                self.resolve_path(repo_root, self.bootloader_elf)
            ),
            "INCLUDE_METADATA_FAULTS:{}".format(include_meta),
            "TOTAL_WRITES:{}".format(total_writes),
        ]

        # Slot B image for OTA simulation.
        if "staging" in self.images:
            vars_list.append(
                "RESILIENT_SLOT_B_BIN:{}".format(
                    self.resolve_path(repo_root, self.images["staging"])
                )
            )

        # Slot A image.
        if "exec" in self.images:
            vars_list.append(
                "RESILIENT_SLOT_A_BIN:{}".format(
                    self.resolve_path(repo_root, self.images["exec"])
                )
            )

        return vars_list


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_int(value: Any, field_name: str) -> int:
    """Parse an integer from YAML (handles hex strings like 0x10000000)."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            pass
    raise ProfileError("{}: expected integer, got {!r}".format(field_name, value))


def _require(data: Dict[str, Any], key: str, context: str = "") -> Any:
    """Require a key to exist in a dict."""
    if key not in data:
        where = " in {}".format(context) if context else ""
        raise ProfileError("missing required field '{}'{}.".format(key, where))
    return data[key]


def _parse_slots(raw: Dict[str, Any]) -> Dict[str, SlotConfig]:
    slots: Dict[str, SlotConfig] = {}
    for name, slot_data in raw.items():
        base = _parse_int(_require(slot_data, "base", "slots.{}".format(name)), "slots.{}.base".format(name))
        size = _parse_int(_require(slot_data, "size", "slots.{}".format(name)), "slots.{}.size".format(name))
        slots[name] = SlotConfig(base=base, size=size)
    return slots


def _parse_memory(raw: Dict[str, Any]) -> MemoryConfig:
    sram = _require(raw, "sram", "memory")
    sram_start = _parse_int(_require(sram, "start", "memory.sram"), "memory.sram.start")
    sram_end = _parse_int(_require(sram, "end", "memory.sram"), "memory.sram.end")
    write_granularity = _parse_int(raw.get("write_granularity", 8), "memory.write_granularity")
    slots = _parse_slots(_require(raw, "slots", "memory"))
    return MemoryConfig(
        sram_start=sram_start,
        sram_end=sram_end,
        write_granularity=write_granularity,
        slots=slots,
    )


def _parse_success_criteria(raw: Optional[Dict[str, Any]]) -> SuccessCriteria:
    if raw is None:
        return SuccessCriteria()
    return SuccessCriteria(
        vtor_in_slot=raw.get("vtor_in_slot"),
        pc_in_slot=raw.get("pc_in_slot"),
        marker_address=_parse_int(raw["marker_address"], "success_criteria.marker_address") if "marker_address" in raw else None,
        marker_value=_parse_int(raw["marker_value"], "success_criteria.marker_value") if "marker_value" in raw else None,
    )


def _parse_fault_sweep(raw: Optional[Dict[str, Any]]) -> FaultSweepConfig:
    if raw is None:
        return FaultSweepConfig()
    fault_types = raw.get("fault_types", ["power_loss"])
    for ft in fault_types:
        if ft not in KNOWN_FAULT_TYPES:
            import warnings
            warnings.warn("Unknown fault type '{}' in profile; ignoring.".format(ft))
        if ft in KNOWN_FAULT_TYPES and ft not in IMPLEMENTED_FAULT_TYPES:
            import warnings
            warnings.warn("Fault type '{}' is not yet implemented; skipping.".format(ft))
    eval_mode = raw.get("evaluation_mode")
    if eval_mode is not None:
        eval_mode = str(eval_mode)
    return FaultSweepConfig(
        mode=raw.get("mode", "runtime"),
        max_writes=raw.get("max_writes", "auto"),
        max_writes_cap=int(raw.get("max_writes_cap", 100000)),
        max_step_limit=int(raw.get("max_step_limit", 500000)),
        run_duration=str(raw.get("run_duration", "0.5")),
        fault_types=fault_types,
        evaluation_mode=eval_mode,
        sweep_strategy=str(raw.get("sweep_strategy", "heuristic")),
    )


def _parse_state_fuzzer(raw: Optional[Dict[str, Any]]) -> StateFuzzerConfig:
    if raw is None:
        return StateFuzzerConfig()
    return StateFuzzerConfig(
        enabled=bool(raw.get("enabled", False)),
        metadata_model=str(raw.get("metadata_model", "ab_replica")),
    )


def _parse_expect(raw: Optional[Dict[str, Any]]) -> ExpectConfig:
    if raw is None:
        return ExpectConfig()
    return ExpectConfig(
        should_find_issues=bool(raw.get("should_find_issues", True)),
        brick_rate_min=float(raw.get("brick_rate_min", 0.0)),
    )


def _parse_pre_boot_state(raw: Optional[list]) -> List[PreBootWrite]:
    if raw is None:
        return []
    writes: List[PreBootWrite] = []
    for i, entry in enumerate(raw):
        addr = _parse_int(_require(entry, "address", "pre_boot_state[{}]".format(i)), "pre_boot_state[{}].address".format(i))
        val = _parse_int(_require(entry, "u32", "pre_boot_state[{}]".format(i)), "pre_boot_state[{}].u32".format(i))
        writes.append(PreBootWrite(address=addr, u32=val))
    return writes


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load_profile(path: str | Path) -> ProfileConfig:
    """Load and validate a YAML profile.

    Args:
        path: Path to the .yaml profile file.

    Returns:
        A validated ProfileConfig.

    Raises:
        ProfileError: If the profile is invalid.
        FileNotFoundError: If the profile doesn't exist.
    """
    if yaml is None:
        raise ProfileError(
            "PyYAML is required for profile loading. Install it: pip install pyyaml"
        )

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("Profile not found: {}".format(path))

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ProfileError("Profile must be a YAML mapping, got {}".format(type(data).__name__))

    # Schema version validation.
    schema_version = _parse_int(
        _require(data, "schema_version"), "schema_version"
    )
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ProfileError(
            "Unsupported schema_version {}. Supported: {}".format(
                schema_version, sorted(SUPPORTED_SCHEMA_VERSIONS)
            )
        )

    # Required fields.
    name = str(_require(data, "name"))
    description = str(data.get("description", ""))
    platform = str(_require(data, "platform"))

    bootloader = _require(data, "bootloader")
    bootloader_elf = str(_require(bootloader, "elf", "bootloader"))
    bootloader_entry = _parse_int(
        _require(bootloader, "entry", "bootloader"), "bootloader.entry"
    )

    memory = _parse_memory(_require(data, "memory"))
    images = {}
    raw_images = data.get("images", {})
    if isinstance(raw_images, dict):
        images = {str(k): str(v) for k, v in raw_images.items()}

    pre_boot_state = _parse_pre_boot_state(data.get("pre_boot_state"))
    setup_script = data.get("setup_script")
    if setup_script is not None:
        setup_script = str(setup_script)

    success_criteria = _parse_success_criteria(data.get("success_criteria"))
    fault_sweep = _parse_fault_sweep(data.get("fault_sweep"))
    state_fuzzer = _parse_state_fuzzer(data.get("state_fuzzer"))
    expect = _parse_expect(data.get("expect"))

    scenario = str(data.get("scenario", "runtime"))
    if scenario not in VALID_SCENARIOS:
        raise ProfileError(
            "Invalid scenario '{}'. Valid: {}".format(scenario, sorted(VALID_SCENARIOS))
        )

    return ProfileConfig(
        schema_version=schema_version,
        name=name,
        description=description,
        platform=platform,
        bootloader_elf=bootloader_elf,
        bootloader_entry=bootloader_entry,
        memory=memory,
        images=images,
        pre_boot_state=pre_boot_state,
        setup_script=setup_script,
        success_criteria=success_criteria,
        fault_sweep=fault_sweep,
        state_fuzzer=state_fuzzer,
        expect=expect,
        profile_path=path,
        scenario=scenario,
    )


def load_profile_raw(path: str | Path) -> Dict[str, Any]:
    """Load a profile as raw dict (for self_test.py to read expect section)."""
    if yaml is None:
        raise ProfileError("PyYAML is required.")
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CLI for debugging
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/profile_loader.py <profile.yaml>", file=sys.stderr)
        return 1

    profile = load_profile(sys.argv[1])
    info = {
        "name": profile.name,
        "description": profile.description,
        "platform": profile.platform,
        "bootloader_elf": profile.bootloader_elf,
        "bootloader_entry": "0x{:08X}".format(profile.bootloader_entry),
        "slots": {
            name: {"base": "0x{:08X}".format(s.base), "size": "0x{:08X}".format(s.size)}
            for name, s in profile.memory.slots.items()
        },
        "images": profile.images,
        "fault_sweep_mode": profile.fault_sweep.mode,
        "max_writes": profile.fault_sweep.max_writes,
        "state_fuzzer_enabled": profile.state_fuzzer.enabled,
        "expect_should_find_issues": profile.expect.should_find_issues,
    }
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
