#!/usr/bin/env python3
"""Run OTA fault campaigns via renode-test + Robot and emit reports."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fault_inject import FaultResult, parse_fault_range

DEFAULT_RENODE_TEST = os.environ.get("RENODE_TEST", "renode-test")
DEFAULT_BUILTIN_ROBOT_SUITE = "tests/builtin_fault_point.robot"
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
    parser.add_argument("--platform-repl", default="platforms/cortex_m0_nvm.repl")
    parser.add_argument("--vulnerable-firmware-elf", default="examples/vulnerable_ota/firmware.elf")
    parser.add_argument("--vulnerable-staging-image", default="examples/test_image.bin")
    parser.add_argument("--resilient-bootloader-elf", default="examples/resilient_ota/bootloader.elf")
    parser.add_argument("--resilient-slot-a-image", default="examples/resilient_ota/slot_a.bin")
    parser.add_argument("--resilient-slot-b-image", default="examples/resilient_ota/slot_b.bin")
    parser.add_argument("--resilient-boot-meta-image", default="examples/resilient_ota/boot_meta.bin")
    parser.add_argument("--fault-range", default="0:28672", help="start:end inclusive")
    parser.add_argument("--fault-step", type=int, default=5000)
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
        help="Fault-point evaluation strategy: fast NVM state evaluation or execution-backed boot check.",
    )
    parser.add_argument(
        "--boot-mode",
        choices=("direct", "swap"),
        default="direct",
        help="A/B evaluation mode: direct slot boot or swap-style staging semantics.",
    )
    parser.add_argument("--include-metadata-faults", action="store_true", help="Inject faults during resilient metadata writes")
    parser.add_argument(
        "--robot-var",
        action="append",
        default=[],
        metavar="KEY:VALUE",
        help="Extra Robot variable (repeatable). Example: --robot-var RENODE_ROOT:/path/to/dir",
    )
    parser.add_argument(
        "--slot-a-image-file",
        default="",
        help="Pre-built image file to seed slot A before A/B campaign runs.",
    )
    parser.add_argument(
        "--slot-b-image-file",
        default="",
        help="Pre-built image file to write directly to slot B during A/B campaigns.",
    )
    parser.add_argument(
        "--ota-header-size",
        type=int,
        default=0,
        help="Image header size in bytes; vectors are read at slot_base + header_size.",
    )
    parser.add_argument("--renode-test", default=DEFAULT_RENODE_TEST)
    parser.add_argument("--robot-suite", default=DEFAULT_BUILTIN_ROBOT_SUITE)
    parser.add_argument("--output", required=True)
    parser.add_argument("--table-output")
    parser.add_argument("--keep-run-artifacts", action="store_true")
    parser.add_argument(
        "--trace-execution",
        action="store_true",
        help="Enable per-point execution traces for manual debugging (A/B fault scripts).",
    )
    parser.add_argument("--no-control", action="store_true", help="Skip automatic unfaulted control run.")
    parser.add_argument(
        "--assert-no-bricks",
        action="store_true",
        help="Exit 1 if any non-control fault point does not boot successfully.",
    )
    parser.add_argument(
        "--assert-control-boots",
        action="store_true",
        help="Exit 1 if any control run does not boot successfully.",
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


def parse_robot_vars(raw_vars: List[str]) -> List[str]:
    parsed: List[str] = []
    for rv in raw_vars:
        key, sep, value = rv.partition(":")
        if not sep or not key or not value:
            raise ValueError("--robot-var must use KEY:VALUE, got '{}'".format(rv))
        parsed.append("{}:{}".format(key, value))
    return parsed


def resolve_input_path(repo_root: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        return str(candidate)
    return str((repo_root / candidate).resolve())


def built_in_scenario_robot_vars(args: argparse.Namespace, repo_root: Path) -> List[str]:
    values = [
        "EVALUATION_MODE:{}".format(args.evaluation_mode),
        "BOOT_MODE:{}".format(args.boot_mode),
        "PLATFORM_REPL:{}".format(resolve_input_path(repo_root, args.platform_repl)),
        "VULNERABLE_FIRMWARE_ELF:{}".format(resolve_input_path(repo_root, args.vulnerable_firmware_elf)),
        "VULNERABLE_STAGING_IMAGE:{}".format(resolve_input_path(repo_root, args.vulnerable_staging_image)),
        "RESILIENT_BOOTLOADER_ELF:{}".format(resolve_input_path(repo_root, args.resilient_bootloader_elf)),
        "RESILIENT_SLOT_A_BIN:{}".format(resolve_input_path(repo_root, args.resilient_slot_a_image)),
        "RESILIENT_SLOT_B_BIN:{}".format(resolve_input_path(repo_root, args.resilient_slot_b_image)),
        "RESILIENT_BOOT_META_BIN:{}".format(resolve_input_path(repo_root, args.resilient_boot_meta_image)),
        # Generic suite compatibility aliases.
        "FIRMWARE_ELF:{}".format(resolve_input_path(repo_root, args.vulnerable_firmware_elf)),
        "BOOTLOADER_ELF:{}".format(resolve_input_path(repo_root, args.resilient_bootloader_elf)),
        "BOOT_META_BIN:{}".format(resolve_input_path(repo_root, args.resilient_boot_meta_image)),
        "OTA_HEADER_SIZE:{}".format(args.ota_header_size),
    ]
    if args.slot_b_image_file:
        values.append("SLOT_B_IMAGE_FILE:{}".format(resolve_input_path(repo_root, args.slot_b_image_file)))
    if args.slot_a_image_file:
        values.append("SLOT_A_IMAGE_FILE:{}".format(resolve_input_path(repo_root, args.slot_a_image_file)))
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
    trace_execution: bool,
    trace_root: Path | None,
    is_control: bool = False,
) -> FaultResult:
    point_kind = "control" if is_control else "fault"
    point_dir = work_dir / "{}_{}_{}".format(scenario, point_kind, fault_at)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"
    trace_file = ""
    if trace_execution:
        if trace_root is None:
            trace_point_dir = point_dir
        else:
            trace_point_dir = trace_root / "{}_{}".format(scenario, fault_at)
            trace_point_dir.mkdir(parents=True, exist_ok=True)
        trace_file = str((trace_point_dir / "execution_trace.log").resolve())

    cmd = [
        renode_test,
        robot_suite,
        "--results-dir",
        str(rf_results),
        "--variable",
        "BUILTIN_SCENARIO:{}".format(scenario),
        "--variable",
        "REPORT_SCENARIO:{}".format(scenario),
        "--variable",
        "FAULT_AT:{}".format(fault_at),
        "--variable",
        "TOTAL_WRITES:{}".format(total_writes),
        "--variable",
        "RESULT_FILE:{}".format(result_file),
        "--variable",
        "INCLUDE_METADATA_FAULTS:{}".format("true" if include_metadata_faults else "false"),
        "--variable",
        "TRACE_EXECUTION:{}".format("true" if trace_execution else "false"),
    ]
    if trace_file:
        cmd.extend(["--variable", "TRACE_FILE:{}".format(trace_file)])

    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
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
        fault_diagnostics=data.get("fault_diagnostics", {}),
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
    trace_execution: bool,
    trace_root: Path | None,
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
                trace_execution=trace_execution,
                trace_root=trace_root,
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
                trace_execution=trace_execution,
                trace_root=trace_root,
                is_control=True,
            )
        )
    return results


def summarize(results: Dict[str, List[FaultResult]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    control_summary: Dict[str, Dict[str, Any]] = {}

    for name, entries in results.items():
        non_control_entries = [entry for entry in entries if not entry.is_control]
        control_entries = [entry for entry in entries if entry.is_control]

        total = len(non_control_entries)
        bricks = sum(1 for r in non_control_entries if r.boot_outcome in {"hard_fault", "hang"})
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
        "boot_mode": args.boot_mode,
        "trace_execution": args.trace_execution,
        "control_enabled": not args.no_control,
        "summary": summary,
        "inputs": {
            "platform_repl": args.platform_repl,
            "vulnerable_firmware_elf": args.vulnerable_firmware_elf,
            "vulnerable_staging_image": args.vulnerable_staging_image,
            "resilient_bootloader_elf": args.resilient_bootloader_elf,
            "resilient_slot_a_image": args.resilient_slot_a_image,
            "resilient_slot_b_image": args.resilient_slot_b_image,
            "resilient_boot_meta_image": args.resilient_boot_meta_image,
            "slot_a_image_file": args.slot_a_image_file,
            "slot_b_image_file": args.slot_b_image_file,
            "ota_header_size": args.ota_header_size,
            "boot_mode": args.boot_mode,
            "trace_execution": args.trace_execution,
            "robot_suite": args.robot_suite,
            "control_enabled": not args.no_control,
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
                                scenario_name,
                                entry.fault_at,
                                entry.boot_outcome,
                            )
                        )
            if failed_points:
                failed_points.append(
                    "  {} bricks out of {} fault points".format(len(failed_points), non_control_points)
                )
                failures.append(("--assert-no-bricks", failed_points))

        if args.assert_control_boots:
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
                                scenario_name,
                                entry.fault_at,
                                entry.boot_outcome,
                            )
                        )
            if control_count == 0:
                raise RuntimeError("--assert-control-boots requested but no control runs were executed")
            if failed_controls:
                failed_controls.append(
                    "  {} failed controls out of {}".format(len(failed_controls), control_count)
                )
                failures.append(("--assert-control-boots", failed_controls))

        return failures

    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    temp_ctx: tempfile.TemporaryDirectory[str] | None = None
    trace_root: Path | None = None

    try:
        if args.no_control and args.assert_control_boots:
            raise ValueError("--assert-control-boots cannot be combined with --no-control")

        renode_test = ensure_tool(args.renode_test)
        robot_suite = args.robot_suite

        points = stepped_fault_points(args.fault_range, args.fault_step)
        vulnerable_total_writes, resilient_total_writes = resolve_total_writes(args.total_writes)
        robot_vars = built_in_scenario_robot_vars(args, repo_root) + parse_robot_vars(args.robot_var)
        cfg = CampaignConfig(
            scenario=args.scenario,
            fault_points=points,
            vulnerable_total_writes=vulnerable_total_writes,
            resilient_total_writes=resilient_total_writes,
            include_metadata_faults=args.include_metadata_faults,
        )

        if args.trace_execution:
            output_path = Path(args.output)
            trace_root = output_path.parent / "{}_traces".format(output_path.stem)
            trace_root.mkdir(parents=True, exist_ok=True)

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
                trace_execution=args.trace_execution,
                trace_root=trace_root,
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
                trace_execution=args.trace_execution,
                trace_root=trace_root,
                include_control=not args.no_control,
            )

        if cfg.scenario not in ("vulnerable", "resilient", "comparative"):
            results[cfg.scenario] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario=cfg.scenario,
                fault_points=cfg.fault_points,
                total_writes=vulnerable_total_writes,
                include_metadata_faults=cfg.include_metadata_faults,
                robot_vars=robot_vars,
                work_dir=work_dir,
                trace_execution=args.trace_execution,
                trace_root=trace_root,
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
