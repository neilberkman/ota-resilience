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
from typing import Dict, List

from fault_inject import FaultResult, parse_fault_range

DEFAULT_RENODE_TEST = os.environ.get("RENODE_TEST", "renode-test")
DEFAULT_ROBOT_SUITE = "tests/ota_fault_point.robot"


@dataclasses.dataclass
class CampaignConfig:
    scenario: str
    fault_points: List[int]
    total_writes: int
    include_metadata_faults: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OTA resilience campaign runner (live renode-test)")
    parser.add_argument("--platform", default="platforms/cortex_m0_mram.repl")
    parser.add_argument("--firmware", default="examples/vulnerable_ota/firmware.elf")
    parser.add_argument("--ota-image", default="examples/test_image.bin")
    parser.add_argument("--fault-range", default="0:28672", help="start:end inclusive")
    parser.add_argument("--fault-step", type=int, default=5000)
    parser.add_argument("--total-writes", type=int, default=28672)
    parser.add_argument("--scenario", choices=["vulnerable", "resilient", "comparative"], default="comparative")
    parser.add_argument("--include-metadata-faults", action="store_true", help="Inject faults during resilient metadata writes")
    parser.add_argument("--renode-test", default=DEFAULT_RENODE_TEST)
    parser.add_argument("--robot-suite", default=DEFAULT_ROBOT_SUITE)
    parser.add_argument("--output", required=True)
    parser.add_argument("--table-output")
    parser.add_argument("--keep-run-artifacts", action="store_true")
    return parser.parse_args()


def stepped_fault_points(expr: str, step: int) -> List[int]:
    if step <= 0:
        raise ValueError("fault-step must be > 0")

    points = list(parse_fault_range(expr))
    selected = points[::step]

    if points and points[-1] not in selected:
        selected.append(points[-1])

    return selected


def ensure_tool(path: str) -> str:
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError("renode-test not found at {}".format(path))
        return path

    resolved = shutil.which(path)
    if resolved is None:
        raise FileNotFoundError("renode-test executable '{}' not found in PATH".format(path))
    return resolved


def run_fault_point(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    scenario: str,
    fault_at: int,
    total_writes: int,
    include_metadata_faults: bool,
    work_dir: Path,
) -> FaultResult:
    point_dir = work_dir / "{}_{}".format(scenario, fault_at)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"

    cmd = [
        renode_test,
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
        mram_state=data.get("mram_state"),
        raw_log=log_output,
    )


def run_campaign(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    scenario: str,
    fault_points: List[int],
    total_writes: int,
    include_metadata_faults: bool,
    work_dir: Path,
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
                work_dir=work_dir,
            )
        )
    return results


def summarize(results: Dict[str, List[FaultResult]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}

    for name, entries in results.items():
        total = len(entries)
        bricks = sum(1 for r in entries if r.boot_outcome in {"hard_fault", "hang"})
        recoveries = sum(1 for r in entries if r.boot_outcome == "success")

        summary[name] = {
            "total": total,
            "bricks": bricks,
            "recoveries": recoveries,
            "brick_rate": (float(bricks) / float(total)) if total else 0.0,
        }

    return summary


def build_comparative_table(vulnerable: List[FaultResult], resilient: List[FaultResult]) -> str:
    rows = ["Fault Point      Copy-Based OTA    A/B Bootloader"]

    vulnerable_by_fault = {r.fault_at: r for r in vulnerable}
    resilient_by_fault = {r.fault_at: r for r in resilient}

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
    summary: Dict[str, Dict[str, float]],
    execution_dir: str,
    repo_root: Path,
    resolved_renode_test: str,
) -> Dict[str, object]:
    if Path(sys.argv[0]).suffix == ".py":
        command_parts = ["python3"] + sys.argv
    else:
        command_parts = sys.argv

    payload: Dict[str, object] = {
        "engine": "renode-test",
        "scenario": cfg.scenario,
        "total_writes": cfg.total_writes,
        "fault_points": cfg.fault_points,
        "include_metadata_faults": cfg.include_metadata_faults,
        "summary": summary,
        "inputs": {
            "platform": args.platform,
            "firmware": args.firmware,
            "ota_image": args.ota_image,
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
    args = parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    renode_test = ensure_tool(args.renode_test)
    robot_suite = args.robot_suite

    points = stepped_fault_points(args.fault_range, args.fault_step)
    cfg = CampaignConfig(
        scenario=args.scenario,
        fault_points=points,
        total_writes=args.total_writes,
        include_metadata_faults=args.include_metadata_faults,
    )

    if args.keep_run_artifacts:
        execution_dir = repo_root / "results" / "renode_runs"
        execution_dir.mkdir(parents=True, exist_ok=True)
        work_dir = execution_dir / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        work_dir.mkdir(parents=True, exist_ok=True)
        report_artifacts_dir = str(work_dir.relative_to(repo_root))
        cleanup = False
    else:
        temp_ctx = tempfile.TemporaryDirectory(prefix="ota_campaign_")
        work_dir = Path(temp_ctx.name)
        report_artifacts_dir = "temporary"
        cleanup = True

    try:
        results: Dict[str, List[FaultResult]] = {}
        if cfg.scenario in ("vulnerable", "comparative"):
            results["vulnerable"] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario="vulnerable",
                fault_points=cfg.fault_points,
                total_writes=cfg.total_writes,
                include_metadata_faults=False,
                work_dir=work_dir,
            )

        if cfg.scenario in ("resilient", "comparative"):
            results["resilient"] = run_campaign(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                scenario="resilient",
                fault_points=cfg.fault_points,
                total_writes=cfg.total_writes,
                include_metadata_faults=cfg.include_metadata_faults,
                work_dir=work_dir,
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
        return 0
    finally:
        if cleanup:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
