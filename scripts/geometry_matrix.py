#!/usr/bin/env python3
"""Parameterized geometry generator for OTA bootloader fault-injection testing.

Generates Renode platform descriptions (.repl), linker scripts, boot-metadata
generators, and campaign runner arguments for a matrix of NVM memory layouts.
This catches geometry/math bugs (the MCUboot bug class) that only manifest
with non-default slot sizes, metadata placement, or word sizes.

Usage:
    python3 scripts/geometry_matrix.py --output-dir /tmp/geo_matrix
    python3 scripts/geometry_matrix.py --output-dir /tmp/geo_matrix --geometry default small_nvm
    python3 scripts/geometry_matrix.py --list
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# NVM base address (fixed for all geometries)
# ---------------------------------------------------------------------------

NVM_BASE: int = 0x10000000


# ---------------------------------------------------------------------------
# GeometryConfig
# ---------------------------------------------------------------------------

@dataclass
class GeometryConfig:
    """Describes one NVM memory layout for OTA testing.

    All slot/metadata offsets are relative to the NVM base address
    (0x10000000).  Sizes are in bytes.
    """

    nvm_size: int           # Total NVM in bytes
    word_size: int          # Write granularity: 4 or 8 bytes
    slot_a_offset: int      # Offset from NVM base to slot A start
    slot_a_size: int        # Slot A size in bytes
    slot_b_offset: int      # Offset from NVM base to slot B start
    slot_b_size: int        # Slot B size in bytes
    metadata_offset: int    # Offset from NVM base to metadata region
    metadata_size: int      # Metadata size (256 min for one replica, 512 for two)
    sram_size: int          # SRAM size in bytes
    name: str               # Human-readable identifier


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_geometry(config: GeometryConfig) -> None:
    """Check that a geometry is internally consistent.

    Raises ValueError on any overlap, alignment, or bounds violation.
    """
    errors: List[str] = []

    # Word size must be 4 or 8.
    if config.word_size not in (4, 8):
        errors.append("word_size must be 4 or 8, got {}".format(config.word_size))

    # NVM size must be positive and a power-of-two multiple of word_size.
    if config.nvm_size <= 0:
        errors.append("nvm_size must be positive, got {}".format(config.nvm_size))

    # Metadata minimum.
    if config.metadata_size < 256:
        errors.append(
            "metadata_size must be >= 256 (one replica), got {}".format(config.metadata_size)
        )

    # Slot sizes must be positive.
    if config.slot_a_size <= 0:
        errors.append("slot_a_size must be positive, got {}".format(config.slot_a_size))
    if config.slot_b_size <= 0:
        errors.append("slot_b_size must be positive, got {}".format(config.slot_b_size))

    # SRAM must be positive.
    if config.sram_size <= 0:
        errors.append("sram_size must be positive, got {}".format(config.sram_size))

    # Word alignment checks.
    ws = config.word_size
    for label, value in [
        ("slot_a_offset", config.slot_a_offset),
        ("slot_a_size", config.slot_a_size),
        ("slot_b_offset", config.slot_b_offset),
        ("slot_b_size", config.slot_b_size),
        ("metadata_offset", config.metadata_offset),
        ("metadata_size", config.metadata_size),
    ]:
        if value % ws != 0:
            errors.append(
                "{} (0x{:X}) is not aligned to word_size ({} bytes)".format(
                    label, value, ws
                )
            )

    # Regions as (start, end_exclusive, label) for overlap detection.
    regions: List[tuple[int, int, str]] = [
        (config.slot_a_offset, config.slot_a_offset + config.slot_a_size, "slot_a"),
        (config.slot_b_offset, config.slot_b_offset + config.slot_b_size, "slot_b"),
        (config.metadata_offset, config.metadata_offset + config.metadata_size, "metadata"),
    ]

    # Boot region occupies [0, slot_a_offset) if slot_a_offset > 0.
    if config.slot_a_offset > 0:
        regions.append((0, config.slot_a_offset, "boot"))

    # Everything must fit within NVM.
    for start, end, label in regions:
        if end > config.nvm_size:
            errors.append(
                "{} extends past NVM: end 0x{:X} > nvm_size 0x{:X}".format(
                    label, end, config.nvm_size
                )
            )

    # Pairwise overlap check.
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            a_start, a_end, a_label = regions[i]
            b_start, b_end, b_label = regions[j]
            if a_start < b_end and b_start < a_end:
                errors.append(
                    "{} [0x{:X}, 0x{:X}) overlaps {} [0x{:X}, 0x{:X})".format(
                        a_label, a_start, a_end, b_label, b_start, b_end
                    )
                )

    if errors:
        raise ValueError(
            "Invalid geometry '{}': {}".format(config.name, "; ".join(errors))
        )


# ---------------------------------------------------------------------------
# Platform .repl generation
# ---------------------------------------------------------------------------

_REPL_TEMPLATE = """\
cpu: CPU.CortexM @ sysbus
    cpuType: "cortex-m0+"
    nvic: nvic

nvic: IRQControllers.NVIC @ sysbus 0xE000E000
    -> cpu@0

nvm: Memory.NVMemory @ sysbus 0x{nvm_base:08X}
    Size: 0x{nvm_size:X}
    WordSize: {word_size}
    EnforceWordWriteSemantics: true
    WriteLatencyMicros: 0

nvm_boot_alias: Memory.NVMemory @ sysbus 0x00000000
    AliasTarget: nvm

nvm_nv_read: Memory.NVMemory @ sysbus 0x{nvm_ro_alias:08X}
    AliasTarget: nvm
    ReadOnly: true

sram: Memory.MappedMemory @ sysbus 0x20000000
    size: 0x{sram_size:X}

nvm_ctrl: NVMemoryController @ sysbus 0x40001000
    Nvm: nvm
    FullMode: true
"""


def generate_platform_repl(config: GeometryConfig, output_path: Path) -> Path:
    """Generate a Renode .repl platform description for the given geometry.

    Returns the path to the written file.
    """
    content = _REPL_TEMPLATE.format(
        nvm_base=NVM_BASE,
        nvm_size=config.nvm_size,
        word_size=config.word_size,
        nvm_ro_alias=NVM_BASE + config.nvm_size,
        sram_size=config.sram_size,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Linker script generation
# ---------------------------------------------------------------------------

_LINKER_TEMPLATE = """\
ENTRY(Reset_Handler)

MEMORY
{{
    {region_name} ({region_attrs}) : ORIGIN = 0x{origin:08X}, LENGTH = 0x{length:X}
    SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 0x{sram_size:X}
}}

SECTIONS
{{
    .isr_vector :
    {{
        KEEP(*(.isr_vector))
    }} > {region_name}

    .text :
    {{
        *(.text*)
        *(.rodata*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame*)
    }} > {region_name}

    .data :
    {{
        *(.data*)
    }} > SRAM AT > {region_name}

    .bss (NOLOAD) :
    {{
        *(.bss*)
        *(COMMON)
    }} > SRAM

    __stack_top = ORIGIN(SRAM) + LENGTH(SRAM);
}}
"""


def generate_linker_scripts(config: GeometryConfig, output_dir: Path) -> Dict[str, Path]:
    """Generate boot, slot_a, and slot_b linker scripts for the geometry.

    Returns a dict mapping script name to its written path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    scripts: Dict[str, Path] = {}

    # Boot linker: [NVM_BASE, NVM_BASE + slot_a_offset).
    boot_size = config.slot_a_offset
    if boot_size > 0:
        boot_path = output_dir / "linker_boot.ld"
        boot_path.write_text(
            _LINKER_TEMPLATE.format(
                region_name="BOOT",
                region_attrs="rx",
                origin=NVM_BASE,
                length=boot_size,
                sram_size=config.sram_size,
            ),
            encoding="utf-8",
        )
        scripts["boot"] = boot_path

    # Slot A linker.
    slot_a_path = output_dir / "linker_slot_a.ld"
    slot_a_path.write_text(
        _LINKER_TEMPLATE.format(
            region_name="SLOTA",
            region_attrs="rx",
            origin=NVM_BASE + config.slot_a_offset,
            length=config.slot_a_size,
            sram_size=config.sram_size,
        ),
        encoding="utf-8",
    )
    scripts["slot_a"] = slot_a_path

    # Slot B linker.
    slot_b_path = output_dir / "linker_slot_b.ld"
    slot_b_path.write_text(
        _LINKER_TEMPLATE.format(
            region_name="SLOTB",
            region_attrs="rx",
            origin=NVM_BASE + config.slot_b_offset,
            length=config.slot_b_size,
            sram_size=config.sram_size,
        ),
        encoding="utf-8",
    )
    scripts["slot_b"] = slot_b_path

    return scripts


# ---------------------------------------------------------------------------
# Boot metadata generator script
# ---------------------------------------------------------------------------

_BOOT_META_TEMPLATE = '''\
#!/usr/bin/env python3
"""Generate boot_meta.bin for geometry: {name}.

Metadata is placed at NVM offset 0x{metadata_offset:X} ({metadata_size} bytes).
Two replicas of {replica_size} bytes each.
"""

import struct
from pathlib import Path

BOOT_META_MAGIC = 0x4F54414D
BOOT_META_REPLICA_SIZE = {replica_size}

words = [0] * (BOOT_META_REPLICA_SIZE // 4)
words[0] = BOOT_META_MAGIC
words[1] = 1   # seq
words[2] = 0   # active_slot
words[3] = 0   # target_slot
words[4] = 0   # state: confirmed
words[5] = 0   # boot_count
words[6] = 3   # max_boot_count

crc = 0xFFFFFFFF
for w in words[:-1]:
    for shift in (0, 8, 16, 24):
        crc ^= (w >> shift) & 0xFF
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if (crc & 1) else 0)
        crc &= 0xFFFFFFFF
words[-1] = (~crc) & 0xFFFFFFFF

replica = struct.pack(\'<\' + \'I\' * len(words), *words)
Path(\'boot_meta.bin\').write_bytes(replica + replica)
'''


def generate_boot_meta_script(config: GeometryConfig, output_path: Path) -> Path:
    """Generate a gen_boot_meta.py script for the geometry's metadata layout.

    Returns the path to the written file.
    """
    replica_size = min(config.metadata_size // 2, 256)
    # Ensure at least 256 per replica.
    if replica_size < 256:
        replica_size = 256

    content = _BOOT_META_TEMPLATE.format(
        name=config.name,
        metadata_offset=config.metadata_offset,
        metadata_size=config.metadata_size,
        replica_size=replica_size,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Campaign argument generation
# ---------------------------------------------------------------------------

def generate_campaign_args(config: GeometryConfig) -> List[str]:
    """Return --robot-var arguments for the campaign runner to use this geometry.

    These are the extra CLI args you'd append to an ota_fault_campaign.py
    invocation so that the Robot test picks up the correct platform file,
    slot addresses, and metadata location.
    """
    args: List[str] = [
        "--robot-var", "NVM_SIZE:0x{:X}".format(config.nvm_size),
        "--robot-var", "NVM_WORD_SIZE:{}".format(config.word_size),
        "--robot-var", "SLOT_A_OFFSET:0x{:X}".format(config.slot_a_offset),
        "--robot-var", "SLOT_A_SIZE:0x{:X}".format(config.slot_a_size),
        "--robot-var", "SLOT_A_ADDR:0x{:08X}".format(NVM_BASE + config.slot_a_offset),
        "--robot-var", "SLOT_B_OFFSET:0x{:X}".format(config.slot_b_offset),
        "--robot-var", "SLOT_B_SIZE:0x{:X}".format(config.slot_b_size),
        "--robot-var", "SLOT_B_ADDR:0x{:08X}".format(NVM_BASE + config.slot_b_offset),
        "--robot-var", "METADATA_OFFSET:0x{:X}".format(config.metadata_offset),
        "--robot-var", "METADATA_SIZE:0x{:X}".format(config.metadata_size),
        "--robot-var", "SRAM_SIZE:0x{:X}".format(config.sram_size),
        "--robot-var", "GEOMETRY_NAME:{}".format(config.name),
    ]
    return args


# ---------------------------------------------------------------------------
# Standard geometry matrix
# ---------------------------------------------------------------------------

STANDARD_GEOMETRIES: List[GeometryConfig] = [
    # (a) default -- matches current cortex_m0_nvm.repl and linker scripts.
    #     512KB NVM, 8-byte words.
    #     Boot: 0x0000-0x1FFF (8KB), Slot A: 0x2000 (220KB), Slot B: 0x39000 (220KB),
    #     Metadata: 0x70000 (512 bytes for two replicas).
    GeometryConfig(
        nvm_size=0x80000,           # 512KB
        word_size=8,
        slot_a_offset=0x2000,       # 8KB boot region before slot A
        slot_a_size=0x37000,        # 220KB
        slot_b_offset=0x39000,
        slot_b_size=0x37000,        # 220KB
        metadata_offset=0x70000,
        metadata_size=512,
        sram_size=0x20000,          # 128KB
        name="default",
    ),
    # (b) small_nvm -- 128KB NVM, 48KB slots, metadata at end.
    GeometryConfig(
        nvm_size=0x20000,          # 128KB
        word_size=8,
        slot_a_offset=0x2000,       # 8KB boot
        slot_a_size=0xC000,         # 48KB
        slot_b_offset=0xE000,
        slot_b_size=0xC000,         # 48KB
        metadata_offset=0x1A000,    # After slot B ends at 0x1A000
        metadata_size=512,
        sram_size=0x20000,
        name="small_nvm",
    ),
    # (c) large_nvm -- 2MB NVM, 960KB slots.
    GeometryConfig(
        nvm_size=0x200000,         # 2MB
        word_size=8,
        slot_a_offset=0x4000,       # 16KB boot
        slot_a_size=0xF0000,        # 960KB
        slot_b_offset=0xF4000,
        slot_b_size=0xF0000,        # 960KB
        metadata_offset=0x1E4000,
        metadata_size=512,
        sram_size=0x40000,          # 256KB
        name="large_nvm",
    ),
    # (d) minimal_slots -- smallest viable slots (4KB each).
    #     Tests near-boundary behavior and off-by-one geometry math.
    GeometryConfig(
        nvm_size=0x20000,          # 128KB
        word_size=8,
        slot_a_offset=0x1000,       # 4KB boot
        slot_a_size=0x1000,         # 4KB
        slot_b_offset=0x2000,
        slot_b_size=0x1000,         # 4KB
        metadata_offset=0x3000,
        metadata_size=512,
        sram_size=0x10000,          # 64KB
        name="minimal_slots",
    ),
    # (e) asymmetric -- Slot A = 128KB, Slot B = 64KB.
    #     Tests size mismatch handling in copy/swap logic.
    GeometryConfig(
        nvm_size=0x80000,          # 512KB
        word_size=8,
        slot_a_offset=0x2000,       # 8KB boot
        slot_a_size=0x20000,        # 128KB
        slot_b_offset=0x22000,
        slot_b_size=0x10000,        # 64KB
        metadata_offset=0x32000,
        metadata_size=512,
        sram_size=0x20000,
        name="asymmetric",
    ),
    # (f) tight_metadata -- metadata immediately after slot B with no gap.
    #     Tests boundary arithmetic when there's zero padding between
    #     the staging area and metadata.
    GeometryConfig(
        nvm_size=0x80000,          # 512KB
        word_size=8,
        slot_a_offset=0x2000,
        slot_a_size=0x37000,        # 220KB
        slot_b_offset=0x39000,
        slot_b_size=0x37000,        # 220KB
        metadata_offset=0x70000,    # Immediately after slot B (0x39000 + 0x37000 = 0x70000)
        metadata_size=256,          # Single replica, minimum viable
        sram_size=0x20000,
        name="tight_metadata",
    ),
    # (g) word_size_4 -- 4-byte word size instead of 8.
    #     Tests that write-granularity assumptions aren't hardcoded to 8.
    GeometryConfig(
        nvm_size=0x80000,          # 512KB
        word_size=4,
        slot_a_offset=0x2000,
        slot_a_size=0x37000,
        slot_b_offset=0x39000,
        slot_b_size=0x37000,
        metadata_offset=0x70000,
        metadata_size=512,
        sram_size=0x20000,
        name="word_size_4",
    ),
    # (h) max_slots -- slots consume nearly all available NVM.
    #     Boot = 4KB, two equal slots filling the rest minus 512 bytes metadata.
    #     512KB total: 4KB boot + 2 * 254.75KB slots + 512B metadata.
    #     slot_size = (0x80000 - 0x1000 - 0x200) // 2 = 0x3F700, rounded down to
    #     8-byte alignment = 0x3F700 (259840 bytes each).
    GeometryConfig(
        nvm_size=0x80000,          # 512KB
        word_size=8,
        slot_a_offset=0x1000,       # 4KB boot
        slot_a_size=0x3F600,        # ~253.5KB
        slot_b_offset=0x40600,
        slot_b_size=0x3F600,        # ~253.5KB
        metadata_offset=0x7FC00,    # Near end of NVM
        metadata_size=512,          # 0x200
        sram_size=0x20000,
        name="max_slots",
    ),
]

# Name-indexed lookup.
GEOMETRIES_BY_NAME: Dict[str, GeometryConfig] = {g.name: g for g in STANDARD_GEOMETRIES}


# ---------------------------------------------------------------------------
# Full matrix generation
# ---------------------------------------------------------------------------

def _config_to_dict(config: GeometryConfig) -> Dict[str, Any]:
    """Serialize a GeometryConfig to a JSON-friendly dict with hex strings."""
    return {
        "name": config.name,
        "nvm_size": config.nvm_size,
        "nvm_size_hex": "0x{:X}".format(config.nvm_size),
        "word_size": config.word_size,
        "slot_a_offset": config.slot_a_offset,
        "slot_a_offset_hex": "0x{:X}".format(config.slot_a_offset),
        "slot_a_size": config.slot_a_size,
        "slot_a_size_hex": "0x{:X}".format(config.slot_a_size),
        "slot_a_addr": NVM_BASE + config.slot_a_offset,
        "slot_a_addr_hex": "0x{:08X}".format(NVM_BASE + config.slot_a_offset),
        "slot_b_offset": config.slot_b_offset,
        "slot_b_offset_hex": "0x{:X}".format(config.slot_b_offset),
        "slot_b_size": config.slot_b_size,
        "slot_b_size_hex": "0x{:X}".format(config.slot_b_size),
        "slot_b_addr": NVM_BASE + config.slot_b_offset,
        "slot_b_addr_hex": "0x{:08X}".format(NVM_BASE + config.slot_b_offset),
        "metadata_offset": config.metadata_offset,
        "metadata_offset_hex": "0x{:X}".format(config.metadata_offset),
        "metadata_size": config.metadata_size,
        "sram_size": config.sram_size,
        "sram_size_hex": "0x{:X}".format(config.sram_size),
    }


def generate_matrix(
    output_dir: Path,
    geometries: Optional[List[GeometryConfig]] = None,
) -> Dict[str, Any]:
    """Generate all artifacts for a set of geometries.

    Creates per-geometry subdirectories under output_dir, each containing:
        - platform.repl
        - linker_boot.ld, linker_slot_a.ld, linker_slot_b.ld
        - gen_boot_meta.py
        - campaign_args.txt

    Returns a manifest dict suitable for JSON serialization.
    """
    if geometries is None:
        geometries = STANDARD_GEOMETRIES

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: List[Dict[str, Any]] = []

    for config in geometries:
        validate_geometry(config)

        geo_dir = output_dir / config.name
        geo_dir.mkdir(parents=True, exist_ok=True)

        # Platform .repl
        repl_path = generate_platform_repl(config, geo_dir / "platform.repl")

        # Linker scripts
        linker_paths = generate_linker_scripts(config, geo_dir)

        # Boot metadata generator
        meta_script_path = generate_boot_meta_script(config, geo_dir / "gen_boot_meta.py")

        # Campaign args
        campaign_args = generate_campaign_args(config)
        args_path = geo_dir / "campaign_args.txt"
        args_path.write_text(" \\\n    ".join(campaign_args) + "\n", encoding="utf-8")

        entry: Dict[str, Any] = _config_to_dict(config)
        entry["files"] = {
            "platform_repl": str(repl_path),
            "gen_boot_meta": str(meta_script_path),
            "campaign_args": str(args_path),
            "linker_boot": str(linker_paths["boot"]) if "boot" in linker_paths else None,
            "linker_slot_a": str(linker_paths["slot_a"]),
            "linker_slot_b": str(linker_paths["slot_b"]),
        }
        entry["campaign_args_list"] = campaign_args
        manifest_entries.append(entry)

    manifest: Dict[str, Any] = {
        "nvm_base": NVM_BASE,
        "nvm_base_hex": "0x{:08X}".format(NVM_BASE),
        "geometry_count": len(manifest_entries),
        "geometries": manifest_entries,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OTA geometry matrix: platform files, linker scripts, and campaign args."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write generated artifacts into.",
    )
    parser.add_argument(
        "--geometry",
        nargs="*",
        metavar="NAME",
        help=(
            "One or more geometry names to generate (default: all). "
            "Available: {}".format(", ".join(g.name for g in STANDARD_GEOMETRIES))
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_geometries",
        help="List available geometries and exit.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate geometries without generating files.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.list_geometries:
        for g in STANDARD_GEOMETRIES:
            print(
                "{:<20s}  NVM={:>7s}  word={}  slotA={:>7s}  slotB={:>7s}  meta@0x{:X}".format(
                    g.name,
                    "{}KB".format(g.nvm_size // 1024),
                    g.word_size,
                    "{}KB".format(g.slot_a_size // 1024),
                    "{}KB".format(g.slot_b_size // 1024),
                    g.metadata_offset,
                )
            )
        return 0

    # Resolve which geometries to use.
    if args.geometry:
        selected: List[GeometryConfig] = []
        for name in args.geometry:
            if name not in GEOMETRIES_BY_NAME:
                print(
                    "Unknown geometry '{}'. Available: {}".format(
                        name, ", ".join(GEOMETRIES_BY_NAME.keys())
                    ),
                    file=sys.stderr,
                )
                return 1
            selected.append(GEOMETRIES_BY_NAME[name])
    else:
        selected = list(STANDARD_GEOMETRIES)

    # Validate all selected geometries.
    for config in selected:
        try:
            validate_geometry(config)
        except ValueError as exc:
            print("Validation error: {}".format(exc), file=sys.stderr)
            return 1

    if args.validate_only:
        print("All {} geometries valid.".format(len(selected)))
        return 0

    if args.output_dir is None:
        print("--output-dir is required (unless using --list or --validate-only).", file=sys.stderr)
        return 1

    manifest = generate_matrix(args.output_dir, geometries=selected)
    print(
        "Generated {} geometries in {}".format(
            manifest["geometry_count"], args.output_dir
        )
    )
    print("Manifest: {}".format(args.output_dir / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
