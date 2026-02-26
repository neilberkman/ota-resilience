#!/usr/bin/env python3
"""Run OTA fault campaigns via renode-test + Robot and emit reports."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fault_inject import FaultResult, MultiFaultResult, parse_fault_range, parse_multi_fault_spec

DEFAULT_RENODE_TEST = os.environ.get("RENODE_TEST", "renode-test")
DEFAULT_ROBOT_SUITE = "tests/ota_fault_point.robot"
DEFAULT_MULTI_FAULT_ROBOT_SUITE = "tests/multi_fault.robot"
DEFAULT_VULNERABLE_TOTAL_WRITES = 28672
DEFAULT_RESILIENT_TOTAL_WRITES = 28160
EXIT_ASSERTION_FAILURE = 1
EXIT_INFRA_FAILURE = 2


@dataclasses.dataclass
class CampaignConfig:
    scenario: str
    fault_points: List[int]
    vulnerable_total_writes: int
    resilient_total_writes: int
    include_metadata_faults: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OTA resilience campaign runner (live renode-test)")
    parser.add_argument("--platform", default="platforms/cortex_m0_nvm.repl")
    parser.add_argument("--firmware", default="examples/vulnerable_ota/firmware.elf")
    parser.add_argument("--ota-image", default="examples/vulnerable_ota/firmware.bin")
    parser.add_argument("--resilient-bootloader-elf", default="examples/resilient_ota/bootloader.elf")
    parser.add_argument("--resilient-slot-a-image", default="examples/resilient_ota/slot_a.bin")
    parser.add_argument("--resilient-slot-b-image", default="examples/resilient_ota/slot_b.bin")
    parser.add_argument("--resilient-boot-meta-image", default="examples/resilient_ota/boot_meta.bin")
    parser.add_argument(
        "--scenario-loader-script",
        default="",
        help="Optional custom loader .resc passed to ota_fault_point.robot as SCENARIO_LOADER_SCRIPT.",
    )
    parser.add_argument(
        "--fault-point-script",
        default="",
        help="Optional custom fault-point .resc passed to ota_fault_point.robot as FAULT_POINT_SCRIPT.",
    )
    parser.add_argument("--fault-range", default="0:28672", help="start:end inclusive")
    parser.add_argument("--fault-step", type=int, default=5000)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a fast smoke subset (first, middle, last fault points) instead of the full stepped set.",
    )
    parser.add_argument(
        "--total-writes",
        type=int,
        default=None,
        help=(
            "Override total NVM word writes for campaign runs. "
            "Default is scenario-specific (vulnerable=28672, resilient=28160)."
        ),
    )
    parser.add_argument("--scenario", default="comparative")
    parser.add_argument(
        "--evaluation-mode",
        choices=("state", "execute"),
        default="execute",
        help="Fault-point evaluation strategy: state-based heuristic or execution-backed boot check.",
    )
    parser.add_argument("--include-metadata-faults", action="store_true", help="Inject faults during resilient metadata writes")
    parser.add_argument(
        "--robot-var",
        action="append",
        default=[],
        metavar="KEY:VALUE",
        help="Extra Robot variable (repeatable). Example: --robot-var OTA_HEADER_SIZE:128",
    )
    parser.add_argument("--renode-test", default=DEFAULT_RENODE_TEST)
    parser.add_argument(
        "--renode-remote-server-dir",
        default="",
        help="Optional directory containing the `renode` remote-server binary wrapper for renode-test.",
    )
    parser.add_argument("--robot-suite", default=DEFAULT_ROBOT_SUITE)
    parser.add_argument("--output", required=True)
    parser.add_argument("--table-output")
    parser.add_argument("--keep-run-artifacts", action="store_true")
    parser.add_argument("--no-control", action="store_true", help="Skip automatic unfaulted control run.")
    parser.add_argument(
        "--assert-no-bricks",
        action="store_true",
        help="Exit 1 if any non-control fault point does not boot successfully.",
    )
    parser.add_argument(
        "--assert-control-boots",
        action="store_true",
        help="Force control-boot assertion on (default behavior).",
    )
    parser.add_argument(
        "--no-assert-control-boots",
        action="store_true",
        help="Disable control-boot assertion (not recommended).",
    )

    # Multi-fault (sequential interruption) options.
    parser.add_argument(
        "--multi-fault",
        action="store_true",
        help="Enable multi-fault mode: inject multiple sequential power losses per run.",
    )
    parser.add_argument(
        "--fault-sequence",
        default="",
        help=(
            "Explicit multi-fault sequence(s). Comma-separated indices per run, "
            "semicolon-separated runs. Example: '100,5000' or '100,5000;200,10000'."
        ),
    )
    parser.add_argument(
        "--multi-fault-random",
        type=int,
        default=0,
        metavar="N",
        help="Generate N random multi-fault sequences (2-3 faults each) within the total_writes range.",
    )
    parser.add_argument(
        "--multi-fault-seed",
        type=int,
        default=None,
        help="RNG seed for --multi-fault-random (for reproducibility).",
    )

    return parser.parse_args()


def stepped_fault_points(expr: str, step: int) -> List[int]:
    if step <= 0:
        raise ValueError("fault-step must be > 0")

    points = list(parse_fault_range(expr))
    selected = points[::step]

    if points and points[-1] not in selected:
        selected.append(points[-1])

    return selected


def quick_fault_points(points: List[int]) -> List[int]:
    if len(points) <= 3:
        return points
    idx_mid = len(points) // 2
    picked = [points[0], points[idx_mid], points[-1]]
    return sorted(set(picked))


def resolve_total_writes(override: int | None) -> tuple[int, int]:
    if override is not None:
        return override, override
    return DEFAULT_VULNERABLE_TOTAL_WRITES, DEFAULT_RESILIENT_TOTAL_WRITES


def ensure_tool(path: str) -> str:
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError("renode-test not found at {}".format(path))
        return path

    resolved = shutil.which(path)
    if resolved is None:
        raise FileNotFoundError("renode-test executable '{}' not found in PATH".format(path))
    return resolved


def resolve_input_path(repo_root: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        return str(candidate)
    return str((repo_root / candidate).resolve())


def parse_robot_vars(raw_vars: List[str]) -> List[str]:
    parsed: List[str] = []
    for rv in raw_vars:
        key, sep, value = rv.partition(":")
        if not sep or not key or not value:
            raise ValueError("--robot-var must use KEY:VALUE, got '{}'".format(rv))
        parsed.append("{}:{}".format(key, value))
    return parsed


def built_in_scenario_robot_vars(args: argparse.Namespace, repo_root: Path) -> List[str]:
    values = [
        "PLATFORM_REPL:{}".format(resolve_input_path(repo_root, args.platform)),
        "VULNERABLE_FIRMWARE_ELF:{}".format(resolve_input_path(repo_root, args.firmware)),
        "VULNERABLE_STAGING_IMAGE:{}".format(resolve_input_path(repo_root, args.ota_image)),
        "RESILIENT_BOOTLOADER_ELF:{}".format(resolve_input_path(repo_root, args.resilient_bootloader_elf)),
        "RESILIENT_SLOT_A_BIN:{}".format(resolve_input_path(repo_root, args.resilient_slot_a_image)),
        "RESILIENT_SLOT_B_BIN:{}".format(resolve_input_path(repo_root, args.resilient_slot_b_image)),
        "RESILIENT_BOOT_META_BIN:{}".format(resolve_input_path(repo_root, args.resilient_boot_meta_image)),
        "EVALUATION_MODE:{}".format(args.evaluation_mode),
        # Generic-name aliases for alternate Robot suites.
        "FIRMWARE_ELF:{}".format(resolve_input_path(repo_root, args.firmware)),
        "BOOTLOADER_ELF:{}".format(resolve_input_path(repo_root, args.resilient_bootloader_elf)),
        "BOOT_META_BIN:{}".format(resolve_input_path(repo_root, args.resilient_boot_meta_image)),
    ]
    if args.scenario_loader_script:
        values.append("SCENARIO_LOADER_SCRIPT:{}".format(resolve_input_path(repo_root, args.scenario_loader_script)))
    if args.fault_point_script:
        values.append("FAULT_POINT_SCRIPT:{}".format(resolve_input_path(repo_root, args.fault_point_script)))
    return values


def run_fault_point(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    scenario: str,
    fault_at: int,
    total_writes: int,
    include_metadata_faults: bool,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    is_control: bool = False,
) -> FaultResult:
    point_kind = "control" if is_control else "fault"
    point_dir = work_dir / "{}_{}_{}".format(scenario, point_kind, fault_at)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"
    bundle_dir = work_dir / ".dotnet_bundle"
    renode_config = work_dir / "renode.config"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        renode_test,
        "--renode-config",
        str(renode_config),
        robot_suite,
        "--results-dir",
        str(rf_results),
        "--variable",
        "SCENARIO:{}".format(scenario),
        "--variable",
        "FAULT_AT:{}".format(fault_at),
        "--variable",
        "TOTAL_WRITES:{}".format(total_writes),
        "--variable",
        "RESULT_FILE:{}".format(result_file),
        "--variable",
        "INCLUDE_METADATA_FAULTS:{}".format("true" if include_metadata_faults else "false"),
    ]
    if renode_remote_server_dir:
        cmd.extend(["--robot-framework-remote-server-full-directory", renode_remote_server_dir])

    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    env = os.environ.copy()
    env.setdefault("DOTNET_BUNDLE_EXTRACT_BASE_DIR", str(bundle_dir))

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "renode-test failed for scenario={} fault_at={}\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                scenario,
                fault_at,
                proc.stdout,
                proc.stderr,
            )
        )

    if not result_file.exists():
        raise RuntimeError("fault point run did not produce {}".format(result_file))

    data = json.loads(result_file.read_text(encoding="utf-8"))
    log_output = proc.stdout.replace(str(work_dir), "<artifacts>")
    log_output = log_output.replace(str(repo_root), "<repo>")
    return FaultResult(
        fault_at=int(data["fault_at"]),
        boot_outcome=str(data["boot_outcome"]),
        boot_slot=data.get("boot_slot"),
        nvm_state=data.get("nvm_state"),
        raw_log=log_output,
        is_control=is_control,
    )


def run_campaign(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    scenario: str,
    fault_points: List[int],
    total_writes: int,
    include_metadata_faults: bool,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    include_control: bool,
) -> List[FaultResult]:
    results: List[FaultResult] = []
    for fault_at in fault_points:
        results.append(
            run_fault_point(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario=scenario,
                fault_at=fault_at,
                total_writes=total_writes,
                include_metadata_faults=include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=renode_remote_server_dir,
            )
        )

    if include_control:
        max_fault_point = max(fault_points) if fault_points else total_writes
        control_fault_at = max(999999, total_writes, max_fault_point) + 1
        results.append(
            run_fault_point(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario=scenario,
                fault_at=control_fault_at,
                total_writes=total_writes,
                include_metadata_faults=include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=renode_remote_server_dir,
                is_control=True,
            )
        )

    return results


def generate_multi_fault_sequences(
    total_writes: int,
    count: int,
    max_faults: int = 3,
    seed: int | None = None,
) -> List[List[int]]:
    """Generate random multi-fault sequences for campaign testing.

    Each sequence is a sorted list of 2 to ``max_faults`` fault indices
    drawn uniformly from [0, total_writes).
    """
    rng = random.Random(seed)
    sequences: List[List[int]] = []
    for _ in range(count):
        num_faults = rng.randint(2, max_faults)
        indices = sorted(rng.sample(range(total_writes), num_faults))
        sequences.append(indices)
    return sequences


def run_multi_fault_point(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    fault_sequence: List[int],
    total_writes: int,
    include_metadata_faults: bool,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    is_control: bool = False,
) -> MultiFaultResult:
    """Run a single multi-fault sequence via the multi_fault.robot suite."""
    seq_label = "_".join(str(f) for f in fault_sequence)
    point_kind = "control" if is_control else "mf"
    point_dir = work_dir / "{}_{}".format(point_kind, seq_label)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"
    bundle_dir = work_dir / ".dotnet_bundle"
    renode_config = work_dir / "renode.config"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    fault_sequence_str = ",".join(str(f) for f in fault_sequence)

    cmd = [
        renode_test,
        "--renode-config",
        str(renode_config),
        robot_suite,
        "--results-dir",
        str(rf_results),
        "--variable",
        "FAULT_SEQUENCE:{}".format(fault_sequence_str),
        "--variable",
        "TOTAL_WRITES:{}".format(total_writes),
        "--variable",
        "RESULT_FILE:{}".format(result_file),
        "--variable",
        "INCLUDE_METADATA_FAULTS:{}".format("true" if include_metadata_faults else "false"),
    ]
    if renode_remote_server_dir:
        cmd.extend(["--robot-framework-remote-server-full-directory", renode_remote_server_dir])

    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    env = os.environ.copy()
    env.setdefault("DOTNET_BUNDLE_EXTRACT_BASE_DIR", str(bundle_dir))

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "renode-test failed for multi-fault sequence={}\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                fault_sequence_str,
                proc.stdout,
                proc.stderr,
            )
        )

    if not result_file.exists():
        raise RuntimeError("multi-fault run did not produce {}".format(result_file))

    data = json.loads(result_file.read_text(encoding="utf-8"))
    log_output = proc.stdout.replace(str(work_dir), "<artifacts>")
    log_output = log_output.replace(str(repo_root), "<repo>")
    return MultiFaultResult(
        fault_sequence=data.get("fault_sequence", fault_sequence),
        boot_outcome=str(data["boot_outcome"]),
        boot_slot=data.get("boot_slot"),
        nvm_state=data.get("nvm_state"),
        per_fault_states=data.get("per_fault_states", []),
        raw_log=log_output,
        is_control=is_control,
    )


def run_multi_fault_campaign(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    sequences: List[List[int]],
    total_writes: int,
    include_metadata_faults: bool,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    include_control: bool,
) -> List[MultiFaultResult]:
    """Run a multi-fault campaign over a list of fault sequences."""
    results: List[MultiFaultResult] = []
    for seq in sequences:
        results.append(
            run_multi_fault_point(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                fault_sequence=seq,
                total_writes=total_writes,
                include_metadata_faults=include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=renode_remote_server_dir,
            )
        )

    if include_control:
        # Control run: fault points far beyond total_writes so no fault is injected.
        control_at = max(999999, total_writes) + 1
        results.append(
            run_multi_fault_point(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                fault_sequence=[control_at, control_at + 1],
                total_writes=total_writes,
                include_metadata_faults=include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=renode_remote_server_dir,
                is_control=True,
            )
        )

    return results


def summarize_multi_fault(results: List[MultiFaultResult]) -> Dict[str, Any]:
    """Summarize multi-fault campaign results."""
    non_control = [r for r in results if not r.is_control]
    control = [r for r in results if r.is_control]
    total = len(non_control)
    bricks = sum(1 for r in non_control if r.boot_outcome != "success")
    recoveries = sum(1 for r in non_control if r.boot_outcome == "success")

    summary: Dict[str, Any] = {
        "total_sequences": total,
        "bricks": bricks,
        "recoveries": recoveries,
        "brick_rate": (float(bricks) / float(total)) if total else 0.0,
        "sequences": [
            {
                "fault_sequence": r.fault_sequence,
                "boot_outcome": r.boot_outcome,
                "boot_slot": r.boot_slot,
                "faults_injected": len(r.per_fault_states),
            }
            for r in non_control
        ],
    }

    if control:
        ctrl = control[-1]
        summary["control"] = {
            "fault_sequence": ctrl.fault_sequence,
            "boot_outcome": ctrl.boot_outcome,
            "boot_slot": ctrl.boot_slot,
        }

    return summary


def summarize(results: Dict[str, List[FaultResult]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    control_summary: Dict[str, Dict[str, Any]] = {}

    for name, entries in results.items():
        non_control_entries = [entry for entry in entries if not entry.is_control]
        control_entries = [entry for entry in entries if entry.is_control]

        total = len(non_control_entries)
        bricks = sum(1 for r in non_control_entries if r.boot_outcome != "success")
        recoveries = sum(1 for r in non_control_entries if r.boot_outcome == "success")

        summary[name] = {
            "total": total,
            "bricks": bricks,
            "recoveries": recoveries,
            "brick_rate": (float(bricks) / float(total)) if total else 0.0,
        }

        if control_entries:
            control_entry = control_entries[-1]
            control_summary[name] = {
                "fault_at": control_entry.fault_at,
                "boot_outcome": control_entry.boot_outcome,
                "boot_slot": control_entry.boot_slot,
            }

    if control_summary:
        if len(control_summary) == 1:
            summary["control"] = next(iter(control_summary.values()))
        else:
            summary["control"] = control_summary

    return summary


def build_comparative_table(vulnerable: List[FaultResult], resilient: List[FaultResult]) -> str:
    rows = ["Fault Point      Copy-Based OTA    A/B Bootloader"]

    vulnerable_by_fault = {r.fault_at: r for r in vulnerable if not r.is_control}
    resilient_by_fault = {r.fault_at: r for r in resilient if not r.is_control}

    all_faults = sorted(set(vulnerable_by_fault.keys()) | set(resilient_by_fault.keys()))
    for fault_at in all_faults:
        v = vulnerable_by_fault.get(fault_at)
        r = resilient_by_fault.get(fault_at)

        if v is None:
            v_cell = "N/A"
        else:
            v_cell = "BRICK" if v.boot_outcome != "success" else "OK (slot {})".format(v.boot_slot or "A")

        if r is None:
            r_cell = "N/A"
        else:
            r_cell = "BRICK" if r.boot_outcome != "success" else "OK (slot {})".format(r.boot_slot or "A")

        rows.append("Write #{:<6}  {:<15} {}".format(fault_at, v_cell, r_cell))

    return "\n".join(rows)


def git_metadata(repo_root: Path) -> Dict[str, str]:
    def run_git(*args: str) -> str:
        proc = subprocess.run(["git"] + list(args), cwd=str(repo_root), capture_output=True, text=True, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else ""

    commit = run_git("rev-parse", "HEAD")
    short_commit = run_git("rev-parse", "--short", "HEAD")
    if not commit:
        commit = "unavailable (no commits yet)"
    if not short_commit:
        short_commit = commit

    return {
        "commit": commit,
        "short_commit": short_commit,
        "dirty": "true" if run_git("status", "--porcelain") else "false",
    }


def to_json_payload(
    args: argparse.Namespace,
    cfg: CampaignConfig,
    results: Dict[str, List[FaultResult]],
    summary: Dict[str, Any],
    execution_dir: str,
    repo_root: Path,
    resolved_renode_test: str,
) -> Dict[str, object]:
    if Path(sys.argv[0]).suffix == ".py":
        command_parts = ["python3"] + sys.argv
    else:
        command_parts = sys.argv

    if cfg.scenario == "vulnerable":
        total_writes_payload: object = cfg.vulnerable_total_writes
    elif cfg.scenario == "resilient":
        total_writes_payload = cfg.resilient_total_writes
    elif cfg.scenario == "comparative":
        total_writes_payload = {
            "vulnerable": cfg.vulnerable_total_writes,
            "resilient": cfg.resilient_total_writes,
        }
    else:
        total_writes_payload = cfg.vulnerable_total_writes

    payload: Dict[str, object] = {
        "engine": "renode-test",
        "scenario": cfg.scenario,
        "total_writes": total_writes_payload,
        "fault_points": cfg.fault_points,
        "include_metadata_faults": cfg.include_metadata_faults,
        "evaluation_mode": args.evaluation_mode,
        "quick": bool(args.quick),
        "control_enabled": not args.no_control,
        "summary": summary,
        "inputs": {
            "platform": args.platform,
            "firmware": args.firmware,
            "ota_image": args.ota_image,
            "resilient_bootloader_elf": args.resilient_bootloader_elf,
            "resilient_slot_a_image": args.resilient_slot_a_image,
            "resilient_slot_b_image": args.resilient_slot_b_image,
            "resilient_boot_meta_image": args.resilient_boot_meta_image,
            "scenario_loader_script": args.scenario_loader_script,
            "fault_point_script": args.fault_point_script,
            "quick": bool(args.quick),
            "robot_suite": args.robot_suite,
            "renode_test": os.path.basename(resolved_renode_test)
            if os.path.isabs(resolved_renode_test)
            else resolved_renode_test,
        },
        "execution": {
            "run_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "campaign_command": " ".join(shlex.quote(a) for a in command_parts),
            "artifacts_dir": execution_dir,
        },
        "git": git_metadata(repo_root),
        "results": {},
    }

    for name, entries in results.items():
        payload["results"][name] = [dataclasses.asdict(e) for e in entries]

    if cfg.scenario == "comparative":
        payload["comparative_table"] = build_comparative_table(results["vulnerable"], results["resilient"])

    return payload


def main() -> int:
    def assertion_failures(args: argparse.Namespace, results: Dict[str, List[FaultResult]]) -> List[Tuple[str, List[str]]]:
        failures: List[Tuple[str, List[str]]] = []

        if args.assert_no_bricks:
            failed_points: List[str] = []
            non_control_points = 0
            for scenario_name, entries in results.items():
                for entry in entries:
                    if entry.is_control:
                        continue
                    non_control_points += 1
                    if entry.boot_outcome != "success":
                        failed_points.append(
                            "  Scenario {} fault point {}: boot_outcome={} (expected success)".format(
                                scenario_name, entry.fault_at, entry.boot_outcome
                            )
                        )
            if failed_points:
                failed_points.append("  {} bricks out of {} fault points".format(len(failed_points), non_control_points))
                failures.append(("--assert-no-bricks", failed_points))

        control_assert_enabled = (not args.no_control) and (args.assert_control_boots or (not args.no_assert_control_boots))
        if control_assert_enabled:
            failed_controls: List[str] = []
            control_count = 0
            for scenario_name, entries in results.items():
                for entry in entries:
                    if not entry.is_control:
                        continue
                    control_count += 1
                    if entry.boot_outcome != "success":
                        failed_controls.append(
                            "  Scenario {} control point {}: boot_outcome={} (expected success)".format(
                                scenario_name, entry.fault_at, entry.boot_outcome
                            )
                        )
            if control_count == 0:
                raise RuntimeError("--assert-control-boots requested but no control runs were executed")
            if failed_controls:
                failed_controls.append("  {} failed controls out of {}".format(len(failed_controls), control_count))
                failures.append(("--assert-control-boots", failed_controls))

        return failures

    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    temp_ctx: tempfile.TemporaryDirectory[str] | None = None

    try:
        if args.no_control and args.assert_control_boots:
            raise ValueError("--assert-control-boots cannot be combined with --no-control")
        if args.assert_control_boots and args.no_assert_control_boots:
            raise ValueError("--assert-control-boots and --no-assert-control-boots are mutually exclusive")

        renode_test = ensure_tool(args.renode_test)
        robot_suite = args.robot_suite

        vulnerable_total_writes, resilient_total_writes = resolve_total_writes(args.total_writes)
        robot_vars = built_in_scenario_robot_vars(args, repo_root) + parse_robot_vars(args.robot_var)

        if args.keep_run_artifacts:
            execution_dir = repo_root / "results" / "renode_runs"
            execution_dir.mkdir(parents=True, exist_ok=True)
            work_dir = execution_dir / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            work_dir.mkdir(parents=True, exist_ok=True)
            report_artifacts_dir = str(work_dir.relative_to(repo_root))
        else:
            temp_ctx = tempfile.TemporaryDirectory(prefix="ota_campaign_")
            work_dir = Path(temp_ctx.name)
            report_artifacts_dir = "temporary"

        # -----------------------------------------------------------------
        # Multi-fault campaign path
        # -----------------------------------------------------------------
        if args.multi_fault or args.fault_sequence or args.multi_fault_random:
            total_writes = resilient_total_writes
            if args.total_writes is not None:
                total_writes = args.total_writes

            # Build the list of fault sequences to test.
            sequences: List[List[int]] = []
            if args.fault_sequence:
                sequences.extend(parse_multi_fault_spec(args.fault_sequence))
            if args.multi_fault_random > 0:
                sequences.extend(
                    generate_multi_fault_sequences(
                        total_writes,
                        args.multi_fault_random,
                        max_faults=3,
                        seed=args.multi_fault_seed,
                    )
                )
            if not sequences:
                raise ValueError(
                    "--multi-fault requires at least one of --fault-sequence or --multi-fault-random"
                )

            mf_robot_suite = robot_suite if robot_suite != DEFAULT_ROBOT_SUITE else DEFAULT_MULTI_FAULT_ROBOT_SUITE
            mf_results = run_multi_fault_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=mf_robot_suite,
                sequences=sequences,
                total_writes=total_writes,
                include_metadata_faults=args.include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
            )

            summary = summarize_multi_fault(mf_results)

            # Build output payload.
            if Path(sys.argv[0]).suffix == ".py":
                command_parts = ["python3"] + sys.argv
            else:
                command_parts = sys.argv

            payload: Dict[str, object] = {
                "engine": "renode-test",
                "mode": "multi-fault",
                "total_writes": total_writes,
                "fault_sequences": [r.fault_sequence for r in mf_results if not r.is_control],
                "include_metadata_faults": args.include_metadata_faults,
                "evaluation_mode": args.evaluation_mode,
                "control_enabled": not args.no_control,
                "summary": summary,
                "inputs": {
                    "platform": args.platform,
                    "resilient_bootloader_elf": args.resilient_bootloader_elf,
                    "resilient_slot_a_image": args.resilient_slot_a_image,
                    "resilient_slot_b_image": args.resilient_slot_b_image,
                    "resilient_boot_meta_image": args.resilient_boot_meta_image,
                    "scenario_loader_script": args.scenario_loader_script,
                    "robot_suite": mf_robot_suite,
                    "renode_test": os.path.basename(renode_test) if os.path.isabs(renode_test) else renode_test,
                    "multi_fault_random": args.multi_fault_random,
                    "multi_fault_seed": args.multi_fault_seed,
                },
                "execution": {
                    "run_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "campaign_command": " ".join(shlex.quote(a) for a in command_parts),
                    "artifacts_dir": report_artifacts_dir,
                },
                "git": git_metadata(repo_root),
                "results": [dataclasses.asdict(r) for r in mf_results],
            }

            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            print(json.dumps(summary, indent=2, sort_keys=True))

            # Assertion checks for multi-fault.
            if args.assert_no_bricks:
                failed_seqs = [r for r in mf_results if not r.is_control and r.boot_outcome != "success"]
                if failed_seqs:
                    print("ASSERTION FAILED: --assert-no-bricks", file=sys.stderr)
                    for r in failed_seqs:
                        print(
                            "  Sequence {}: boot_outcome={} (expected success)".format(
                                r.fault_sequence, r.boot_outcome
                            ),
                            file=sys.stderr,
                        )
                    print(
                        "  {} bricks out of {} sequences".format(
                            len(failed_seqs), len([r for r in mf_results if not r.is_control])
                        ),
                        file=sys.stderr,
                    )
                    return EXIT_ASSERTION_FAILURE

            return 0

        # -----------------------------------------------------------------
        # Standard single-fault campaign path
        # -----------------------------------------------------------------
        points = stepped_fault_points(args.fault_range, args.fault_step)
        if args.quick:
            points = quick_fault_points(points)
        if args.scenario not in ("vulnerable", "resilient", "comparative") and args.total_writes is None:
            raise ValueError("--total-writes is required for custom scenarios")

        cfg = CampaignConfig(
            scenario=args.scenario,
            fault_points=points,
            vulnerable_total_writes=vulnerable_total_writes,
            resilient_total_writes=resilient_total_writes,
            include_metadata_faults=args.include_metadata_faults,
        )

        results: Dict[str, List[FaultResult]] = {}
        if cfg.scenario in ("vulnerable", "comparative"):
            results["vulnerable"] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario="vulnerable",
                fault_points=cfg.fault_points,
                total_writes=cfg.vulnerable_total_writes,
                include_metadata_faults=False,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
            )

        if cfg.scenario in ("resilient", "comparative"):
            results["resilient"] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario="resilient",
                fault_points=cfg.fault_points,
                total_writes=cfg.resilient_total_writes,
                include_metadata_faults=cfg.include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
            )

        if cfg.scenario not in ("vulnerable", "resilient", "comparative"):
            results[cfg.scenario] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario=cfg.scenario,
                fault_points=cfg.fault_points,
                total_writes=cfg.vulnerable_total_writes,
                include_metadata_faults=cfg.include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
            )

        summary = summarize(results)
        payload = to_json_payload(args, cfg, results, summary, report_artifacts_dir, repo_root, renode_test)

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

        if args.table_output:
            table_path = Path(args.table_output)
            table_path.parent.mkdir(parents=True, exist_ok=True)
            if cfg.scenario == "comparative":
                table_path.write_text(str(payload["comparative_table"]) + "\n", encoding="utf-8")
            else:
                table_path.write_text("no comparative table for single-scenario campaign\n", encoding="utf-8")

        print(json.dumps(summary, indent=2, sort_keys=True))

        failures = assertion_failures(args, results)
        if failures:
            for flag, lines in failures:
                print("ASSERTION FAILED: {}".format(flag), file=sys.stderr)
                for line in lines:
                    print(line, file=sys.stderr)
            return EXIT_ASSERTION_FAILURE

        return 0
    except Exception as exc:
        print("INFRASTRUCTURE FAILURE: {}".format(exc), file=sys.stderr)
        return EXIT_INFRA_FAILURE
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
