#!/usr/bin/env python3
"""Profile-driven bootloader audit via runtime fault sweep.

Loads a declarative YAML profile, runs fault injection at every NVM write
point during an OTA update, and reports which fault points result in a
bricked device.

Usage::

    python3 scripts/audit_bootloader.py \\
        --profile profiles/naive_bare_copy.yaml \\
        --output results/naive_audit.json

    python3 scripts/audit_bootloader.py \\
        --profile profiles/resilient_none.yaml \\
        --output results/resilient_audit.json \\
        --quick
"""

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
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fault_inject import FaultResult
from profile_loader import ProfileConfig, load_profile

DEFAULT_RENODE_TEST = os.environ.get("RENODE_TEST", "renode-test")
DEFAULT_ROBOT_SUITE = "tests/ota_fault_point.robot"
EXIT_ASSERTION_FAILURE = 1
EXIT_INFRA_FAILURE = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile-driven bootloader fault-injection audit."
    )
    parser.add_argument(
        "--profile", required=True,
        help="Path to a YAML bootloader profile.",
    )
    parser.add_argument("--output", required=True, help="Output JSON report path.")
    parser.add_argument(
        "--evaluation-mode",
        choices=("state", "execute"),
        default="state",
        help="Fault evaluation: state (fast Python simulation) or execute (CPU boot). Default: state.",
    )
    parser.add_argument("--renode-test", default=DEFAULT_RENODE_TEST)
    parser.add_argument(
        "--renode-remote-server-dir", default="",
        help="Optional directory containing the renode remote-server binary.",
    )
    parser.add_argument("--robot-suite", default=DEFAULT_ROBOT_SUITE)
    parser.add_argument(
        "--robot-var", action="append", default=[], metavar="KEY:VALUE",
        help="Extra Robot variable (repeatable).",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Run a smoke subset (first, middle, last fault points).",
    )
    parser.add_argument(
        "--fault-step", type=int, default=1,
        help="Step between fault points (default: 1 = test every write).",
    )
    parser.add_argument(
        "--fault-start", type=int, default=None,
        help="First fault point to test (default: 0).",
    )
    parser.add_argument(
        "--fault-end", type=int, default=None,
        help="Last fault point to test (exclusive; default: max_writes).",
    )
    parser.add_argument("--keep-run-artifacts", action="store_true")
    parser.add_argument(
        "--no-control", action="store_true",
        help="Skip automatic unfaulted control run.",
    )
    parser.add_argument(
        "--no-assert-control-boots", action="store_true",
        help="Disable control-boot assertion.",
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Number of parallel Renode instances (default: 1).",
    )
    parser.add_argument(
        "--no-trace-replay", action="store_true",
        help="Disable trace replay optimization; force full CPU execution for every fault point.",
    )
    return parser.parse_args()


def ensure_tool(path: str) -> str:
    if os.path.isabs(path):
        if not os.path.exists(path):
            raise FileNotFoundError("renode-test not found at {}".format(path))
        return path
    resolved = shutil.which(path)
    if resolved is None:
        raise FileNotFoundError(
            "renode-test executable '{}' not found in PATH".format(path)
        )
    return resolved


def parse_robot_vars(raw_vars: List[str]) -> List[str]:
    parsed: List[str] = []
    for rv in raw_vars:
        key, sep, value = rv.partition(":")
        if not sep or not key or not value:
            raise ValueError("--robot-var must use KEY:VALUE, got '{}'".format(rv))
        parsed.append("{}:{}".format(key, value))
    return parsed


def quick_subset(points: List[int]) -> List[int]:
    if len(points) <= 3:
        return points
    mid = len(points) // 2
    return sorted(set([points[0], points[mid], points[-1]]))


def run_single_point(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    profile: ProfileConfig,
    fault_at: int,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    is_control: bool = False,
    calibration: bool = False,
) -> Dict[str, Any]:
    """Run a single fault point (or calibration) via renode-test."""
    label = "calibration" if calibration else ("control" if is_control else "fault_{}".format(fault_at))
    point_dir = work_dir / "{}_{}".format(profile.name, label)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"
    bundle_dir = work_dir / ".dotnet_bundle"
    renode_config = work_dir / "renode.config"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        renode_test,
        "--renode-config", str(renode_config),
        robot_suite,
        "--results-dir", str(rf_results),
        "--variable", "FAULT_AT:{}".format(fault_at),
        "--variable", "RESULT_FILE:{}".format(result_file),
        "--variable", "CALIBRATION_MODE:{}".format("true" if calibration else "false"),
    ]
    if renode_remote_server_dir:
        cmd.extend(["--robot-framework-remote-server-full-directory", renode_remote_server_dir])

    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    env = os.environ.copy()
    env.setdefault("DOTNET_BUNDLE_EXTRACT_BASE_DIR", str(bundle_dir))

    proc = subprocess.run(
        cmd, cwd=str(repo_root),
        capture_output=True, text=True, check=False, env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "renode-test failed for {} fault_at={}\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                label, fault_at, proc.stdout, proc.stderr,
            )
        )

    if not result_file.exists():
        raise RuntimeError("Run did not produce {}".format(result_file))

    return json.loads(result_file.read_text(encoding="utf-8"))


@dataclasses.dataclass
class CalibrationResult:
    total_writes: int
    total_erases: int
    trace_file: Optional[str]
    erase_trace_file: Optional[str]
    calibration_exec_hash: Optional[str] = None


def run_calibration(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    profile: ProfileConfig,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
) -> CalibrationResult:
    """Run calibration to discover total NVM writes and erases during a clean update."""
    data = run_single_point(
        repo_root=repo_root,
        renode_test=renode_test,
        robot_suite=robot_suite,
        profile=profile,
        fault_at=0,  # ignored in calibration
        robot_vars=robot_vars,
        work_dir=work_dir,
        renode_remote_server_dir=renode_remote_server_dir,
        calibration=True,
    )
    total_writes = int(data.get("total_writes", 0))
    total_erases = int(data.get("total_erases", 0))
    if total_writes <= 0 and total_erases <= 0:
        raise RuntimeError(
            "Calibration returned total_writes={}, total_erases={} — bootloader may not be "
            "writing to NVM during emulation.".format(total_writes, total_erases)
        )
    cap = profile.fault_sweep.max_writes_cap
    if total_writes > cap:
        print(
            "WARNING: Calibration found {} writes, capping to {}".format(
                total_writes, cap
            ),
            file=sys.stderr,
        )
        total_writes = cap
    return CalibrationResult(
        total_writes=total_writes,
        total_erases=total_erases,
        trace_file=data.get("trace_file"),
        erase_trace_file=data.get("erase_trace_file"),
        calibration_exec_hash=data.get("calibration_exec_hash"),
    )


def run_batch(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    profile: ProfileConfig,
    fault_points: List[int],
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    trace_file: Optional[str] = None,
    erase_trace_file: Optional[str] = None,
    fault_types_list: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Run multiple fault points in a single Renode session (batch mode).

    fault_types_list: parallel list of fault types ('w' or 'e') per fault point.
    """
    batch_dir = work_dir / "{}_batch".format(profile.name)
    batch_dir.mkdir(parents=True, exist_ok=True)

    result_file = batch_dir / "result.json"
    rf_results = batch_dir / "robot"
    bundle_dir = work_dir / ".dotnet_bundle"
    renode_config = work_dir / "renode.config"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    csv = ",".join(str(fp) for fp in fault_points)
    ft_csv = ",".join(fault_types_list) if fault_types_list else ""

    # Determine fault_types mode for the .resc.
    has_erase = fault_types_list and 'e' in fault_types_list
    has_write = fault_types_list and 'w' in fault_types_list
    if has_erase and has_write:
        fault_types_mode = "both"
    elif has_erase:
        fault_types_mode = "erase"
    else:
        fault_types_mode = "write"

    cmd = [
        renode_test,
        "--renode-config", str(renode_config),
        robot_suite,
        "--results-dir", str(rf_results),
        "--variable", "FAULT_POINTS_CSV:{}".format(csv),
        "--variable", "FAULT_AT:0",
        "--variable", "RESULT_FILE:{}".format(result_file),
        "--variable", "CALIBRATION_MODE:false",
        "--variable", "TRACE_FILE:{}".format(trace_file or ""),
        "--variable", "ERASE_TRACE_FILE:{}".format(erase_trace_file or ""),
        "--variable", "FAULT_TYPES:{}".format(fault_types_mode),
        "--variable", "FAULT_TYPE_CSV:{}".format(ft_csv),
    ]
    if renode_remote_server_dir:
        cmd.extend(["--robot-framework-remote-server-full-directory", renode_remote_server_dir])

    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    env = os.environ.copy()
    env.setdefault("DOTNET_BUNDLE_EXTRACT_BASE_DIR", str(bundle_dir))

    proc = subprocess.run(
        cmd, cwd=str(repo_root),
        capture_output=True, text=True, check=False, env=env,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "renode-test batch failed\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                proc.stdout, proc.stderr,
            )
        )

    if not result_file.exists():
        raise RuntimeError("Batch run did not produce {}".format(result_file))

    data = json.loads(result_file.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return [data]


def normalize_classic_result(data: Dict[str, Any], fault_at: int) -> Dict[str, Any]:
    """Normalize a classic .resc result to the runtime sweep format."""
    nvm = data.get("nvm_state", {})
    return {
        "fault_at": fault_at,
        "fault_requested": fault_at,
        "fault_injected": nvm.get("faulted", False),
        "fault_address": nvm.get("fault_address", "0x00000000"),
        "boot_outcome": data.get("boot_outcome", "hard_fault"),
        "boot_slot": data.get("boot_slot"),
        "actual_writes": nvm.get("write_index", 0),
        "signals": {
            "evaluation_mode": nvm.get("evaluation_mode", "state"),
            "chosen_slot": nvm.get("chosen_slot"),
            "requested_slot": nvm.get("requested_slot"),
            "replica0_valid": nvm.get("replica0_valid"),
            "replica1_valid": nvm.get("replica1_valid"),
        },
    }


def run_classic_sweep(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    profile: ProfileConfig,
    fault_points: List[int],
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    include_control: bool,
) -> List[Dict[str, Any]]:
    """Run fault sweep using classic per-point .resc (for resilient/vulnerable scenarios)."""
    results: List[Dict[str, Any]] = []

    for fp in fault_points:
        data = run_single_point(
            repo_root=repo_root,
            renode_test=renode_test,
            robot_suite=robot_suite,
            profile=profile,
            fault_at=fp,
            robot_vars=robot_vars,
            work_dir=work_dir,
            renode_remote_server_dir=renode_remote_server_dir,
        )
        result = normalize_classic_result(data, fp)
        result["is_control"] = False
        results.append(result)

    if include_control:
        max_fp = max(fault_points) if fault_points else 999999
        control_at = max(999999, max_fp) + 1
        data = run_single_point(
            repo_root=repo_root,
            renode_test=renode_test,
            robot_suite=robot_suite,
            profile=profile,
            fault_at=control_at,
            robot_vars=robot_vars,
            work_dir=work_dir,
            renode_remote_server_dir=renode_remote_server_dir,
            is_control=True,
        )
        result = normalize_classic_result(data, control_at)
        result["is_control"] = True
        results.append(result)

    return results


def _run_batch_worker(
    repo_root_str: str,
    renode_test: str,
    robot_suite: str,
    profile_path: str,
    fault_points: List[int],
    robot_vars: List[str],
    work_dir_str: str,
    renode_remote_server_dir: str,
    worker_id: int,
    trace_file: Optional[str] = None,
    erase_trace_file: Optional[str] = None,
    fault_types_list: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Worker function for parallel batch execution.

    Runs in a subprocess via ProcessPoolExecutor.  Reloads the profile
    from disk so everything is picklable.
    """
    repo_root = Path(repo_root_str)
    work_dir = Path(work_dir_str)
    worker_dir = work_dir / "worker_{}".format(worker_id)
    worker_dir.mkdir(parents=True, exist_ok=True)

    # Re-create the renode config for this worker's directory.
    renode_config = worker_dir / "renode.config"
    renode_config.write_text(
        "[general]\n"
        "terminal = Termsharp\n"
        "compiler-cache-enabled = False\n"
        "serialization-mode = Generated\n"
        "use-synchronous-logging = False\n"
        "always-log-machine-name = False\n"
        "collapse-repeated-log-entries = True\n"
        "log-history-limit = 1000\n"
        "store-table-bits = 41\n"
        "[monitor]\n"
        "consume-exceptions-from-command = True\n"
        "break-script-on-exception = True\n"
        "number-format = Hexadecimal\n"
        "[plugins]\n"
        "enabled-plugins = \n"
        "[translation]\n"
        "min-tb-size = 33554432\n"
        "max-tb-size = 536870912\n",
        encoding="utf-8",
    )

    profile = load_profile(profile_path)

    return run_batch(
        repo_root=repo_root,
        renode_test=renode_test,
        robot_suite=robot_suite,
        profile=profile,
        fault_points=fault_points,
        robot_vars=robot_vars,
        work_dir=worker_dir,
        renode_remote_server_dir=renode_remote_server_dir,
        trace_file=trace_file,
        erase_trace_file=erase_trace_file,
        fault_types_list=fault_types_list,
    )


def run_runtime_sweep(
    repo_root: Path,
    renode_test: str,
    robot_suite: str,
    profile: ProfileConfig,
    fault_points: List[int],
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    include_control: bool,
    num_workers: int = 1,
    trace_file: Optional[str] = None,
    erase_trace_file: Optional[str] = None,
    fault_types_list: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Run the full runtime fault sweep.

    Uses batch mode (single Renode session) for all fault points, then
    runs the control point separately.  When num_workers > 1, fault
    points are split across parallel Renode instances.

    If trace_file is provided, uses trace-replay mode: reconstructs
    flash state from the calibration trace instead of re-emulating
    Phase 1.  This eliminates the O(N^2) prefix cost.

    fault_types_list: parallel list of 'w' or 'e' per fault point.
    """
    if fault_points and num_workers > 1:
        # Split fault points into roughly equal chunks.
        n = min(num_workers, len(fault_points))
        chunk_size = (len(fault_points) + n - 1) // n
        chunks = [fault_points[i:i + chunk_size] for i in range(0, len(fault_points), chunk_size)]
        ft_chunks: List[Optional[List[str]]] = []
        if fault_types_list:
            ft_chunks = [fault_types_list[i:i + chunk_size] for i in range(0, len(fault_types_list), chunk_size)]
        else:
            ft_chunks = [None] * len(chunks)

        print(
            "Parallel sweep: {} workers, chunks of ~{} points".format(
                len(chunks), chunk_size
            ),
            file=sys.stderr,
        )

        batch_results: List[Dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=len(chunks)) as pool:
            futures = {}
            for wid, chunk in enumerate(chunks):
                f = pool.submit(
                    _run_batch_worker,
                    repo_root_str=str(repo_root),
                    renode_test=renode_test,
                    robot_suite=robot_suite,
                    profile_path=str(profile.profile_path),
                    fault_points=chunk,
                    robot_vars=robot_vars,
                    work_dir_str=str(work_dir),
                    renode_remote_server_dir=renode_remote_server_dir,
                    worker_id=wid,
                    trace_file=trace_file,
                    erase_trace_file=erase_trace_file,
                    fault_types_list=ft_chunks[wid] if wid < len(ft_chunks) else None,
                )
                futures[f] = wid

            for f in as_completed(futures):
                wid = futures[f]
                try:
                    worker_results = f.result()
                    batch_results.extend(worker_results)
                    print(
                        "Worker {} finished: {} results".format(wid, len(worker_results)),
                        file=sys.stderr,
                    )
                except Exception as exc:
                    print(
                        "Worker {} FAILED: {}".format(wid, exc),
                        file=sys.stderr,
                    )
                    raise
    elif fault_points:
        batch_results = run_batch(
            repo_root=repo_root,
            renode_test=renode_test,
            robot_suite=robot_suite,
            profile=profile,
            fault_points=fault_points,
            robot_vars=robot_vars,
            work_dir=work_dir,
            renode_remote_server_dir=renode_remote_server_dir,
            trace_file=trace_file,
            erase_trace_file=erase_trace_file,
            fault_types_list=fault_types_list,
        )
    else:
        batch_results = []

    results: List[Dict[str, Any]] = []
    for data in batch_results:
        data["is_control"] = False
        results.append(data)

    # Control point runs separately (fault_at far beyond max writes).
    if include_control:
        max_fp = max(fault_points) if fault_points else 999999
        control_at = max(999999, max_fp) + 1
        data = run_single_point(
            repo_root=repo_root,
            renode_test=renode_test,
            robot_suite=robot_suite,
            profile=profile,
            fault_at=control_at,
            robot_vars=robot_vars,
            work_dir=work_dir,
            renode_remote_server_dir=renode_remote_server_dir,
            is_control=True,
        )
        data["is_control"] = True
        results.append(data)

    return results


def categorize_failure(
    result: Dict[str, Any],
    total_writes: int,
    profile: ProfileConfig,
) -> Dict[str, Any]:
    """Classify a single failure by outcome type and fault region."""
    fp = result.get("fault_at", 0)
    outcome = result.get("boot_outcome", "unknown")
    fault_addr = result.get("fault_address", "0x00000000")

    # Parse fault address.
    if isinstance(fault_addr, str):
        addr = int(fault_addr, 16)
    else:
        addr = int(fault_addr)

    # Determine which memory region the faulted write targeted.
    # MCUboot puts trailers at the end of each slot (last page), so
    # check trailer before data to get the more specific classification.
    region = "unknown"
    page_size = getattr(profile.memory, "page_size", 4096)
    for slot_name, slot_info in profile.memory.slots.items():
        slot_end = slot_info.base + slot_info.size
        if slot_end - page_size <= addr < slot_end:
            region = slot_name + "_trailer"
            break
        if slot_info.base <= addr < slot_end:
            region = slot_name + "_data"
            break

    # Swap phase based on position.
    if total_writes > 0:
        pct = fp / total_writes
    else:
        pct = 0.0
    if pct < 0.01:
        phase = "early"
    elif pct > 0.99:
        phase = "late"
    else:
        phase = "mid"

    return {
        "fault_at": fp,
        "outcome": outcome,
        "fault_address": fault_addr,
        "region": region,
        "phase": phase,
        "position_pct": round(pct * 100, 2),
    }


def summarize_runtime_sweep(
    results: List[Dict[str, Any]],
    total_writes: int = 0,
    profile: Optional["ProfileConfig"] = None,
) -> Dict[str, Any]:
    """Compute summary statistics from runtime sweep results."""
    non_control = [r for r in results if not r.get("is_control", False)]
    control = [r for r in results if r.get("is_control", False)]

    # Fail-closed: exclude points where fault didn't actually fire.
    injected = [r for r in non_control if r.get("fault_injected", False)]
    not_injected = [r for r in non_control if not r.get("fault_injected", False)]

    total = len(injected)
    failures = [r for r in injected if r.get("boot_outcome") != "success"]
    recoveries = sum(1 for r in injected if r.get("boot_outcome") == "success")

    # Categorize failures by outcome type.
    outcome_counts: Dict[str, int] = {}
    categorized_failures: List[Dict[str, Any]] = []
    for r in failures:
        outcome = r.get("boot_outcome", "unknown")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if profile:
            categorized_failures.append(
                categorize_failure(r, total_writes, profile)
            )

    summary: Dict[str, Any] = {
        "total_fault_points": total,
        "bricks": len(failures),
        "recoveries": recoveries,
        "brick_rate": (float(len(failures)) / float(total)) if total else 0.0,
        "discarded_no_fault_fired": len(not_injected),
        "failure_outcomes": outcome_counts,
    }

    if categorized_failures:
        summary["failures"] = categorized_failures

    if control:
        ctrl = control[-1]
        summary["control"] = {
            "boot_outcome": ctrl.get("boot_outcome"),
            "boot_slot": ctrl.get("boot_slot"),
        }

    return summary


def git_metadata(repo_root: Path) -> Dict[str, str]:
    def run_git(*args: str) -> str:
        proc = subprocess.run(
            ["git"] + list(args), cwd=str(repo_root),
            capture_output=True, text=True, check=False,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""

    commit = run_git("rev-parse", "HEAD")
    short_commit = run_git("rev-parse", "--short", "HEAD")
    if not commit:
        commit = "unavailable"
    if not short_commit:
        short_commit = commit

    return {
        "commit": commit,
        "short_commit": short_commit,
        "dirty": "true" if run_git("status", "--porcelain") else "false",
    }


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    temp_ctx: Optional[tempfile.TemporaryDirectory[str]] = None

    try:
        renode_test = ensure_tool(args.renode_test)
        profile = load_profile(args.profile)
        robot_suite = args.robot_suite

        if profile.success_criteria.image_hash:
            print("Discovery mode: image hash validation enabled.", file=sys.stderr)
        if profile.update_trigger:
            print(
                "Update trigger: {} on slot '{}' ({} pre_boot writes generated).".format(
                    profile.update_trigger.type,
                    profile.update_trigger.slot,
                    len(profile.pre_boot_state),
                ),
                file=sys.stderr,
            )

        # Resolve evaluation mode: profile default, then CLI override.
        eval_mode = args.evaluation_mode
        if profile.fault_sweep.evaluation_mode and not any(
            a.startswith("--evaluation-mode") for a in sys.argv
        ):
            eval_mode = profile.fault_sweep.evaluation_mode

        # Build robot vars from profile + CLI extras.
        robot_vars = profile.robot_vars(repo_root) + parse_robot_vars(args.robot_var)
        robot_vars.append("EVALUATION_MODE:{}".format(eval_mode))

        # Work directory.
        if args.keep_run_artifacts:
            execution_dir = repo_root / "results" / "audit_runs"
            execution_dir.mkdir(parents=True, exist_ok=True)
            work_dir = execution_dir / dt.datetime.now(dt.timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ"
            )
            work_dir.mkdir(parents=True, exist_ok=True)
            report_artifacts_dir = str(work_dir.relative_to(repo_root))
        else:
            temp_ctx = tempfile.TemporaryDirectory(prefix="ota_audit_")
            work_dir = Path(temp_ctx.name)
            report_artifacts_dir = "temporary"

        # -------------------------------------------------------------------
        # Calibration
        # -------------------------------------------------------------------
        max_writes = profile.fault_sweep.max_writes
        trace_file: Optional[str] = None
        erase_trace_file: Optional[str] = None
        total_erases: int = 0
        # Determine if erase fault injection is requested.
        fault_types = profile.fault_sweep.fault_types
        include_erases = "interrupted_erase" in fault_types

        # Pass fault_types to calibration so erase trace is captured.
        if include_erases:
            robot_vars.append("FAULT_TYPES:both")

        if max_writes == "auto":
            if eval_mode == "state" and "exec" in profile.memory.slots:
                # State mode: compute write count from slot geometry.
                exec_slot = profile.memory.slots["exec"]
                max_writes = exec_slot.size // profile.memory.write_granularity
                print("Computed write count from slot geometry: {} writes.".format(max_writes), file=sys.stderr)
            else:
                print("Calibrating write count for '{}'...".format(profile.name), file=sys.stderr)
                cal = run_calibration(
                    repo_root=repo_root,
                    renode_test=renode_test,
                    robot_suite=robot_suite,
                    profile=profile,
                    robot_vars=robot_vars,
                    work_dir=work_dir,
                    renode_remote_server_dir=args.renode_remote_server_dir,
                )
                max_writes = cal.total_writes
                total_erases = cal.total_erases
                trace_file = cal.trace_file
                erase_trace_file = cal.erase_trace_file
                # For image hash discovery mode: use calibration-computed
                # exec hash as the ground truth for what a successful
                # operation produces.
                if cal.calibration_exec_hash:
                    robot_vars.append(
                        "EXPECTED_EXEC_SHA256:{}".format(cal.calibration_exec_hash)
                    )
                    print(
                        "Calibration: exec slot hash = {}...".format(
                            cal.calibration_exec_hash[:16]
                        ),
                        file=sys.stderr,
                    )
                if include_erases:
                    print("Calibration: {} NVM writes, {} page erases.".format(max_writes, total_erases), file=sys.stderr)
                else:
                    print("Calibration: {} NVM writes.".format(max_writes), file=sys.stderr)
        else:
            max_writes = int(max_writes)

        # Apply safety cap.
        cap = profile.fault_sweep.max_writes_cap
        if max_writes > cap:
            print(
                "Capping max_writes from {} to {}".format(max_writes, cap),
                file=sys.stderr,
            )
            max_writes = cap

        # -------------------------------------------------------------------
        # Build fault point list
        # -------------------------------------------------------------------
        heuristic_summary: Optional[Dict] = None
        use_heuristic = (
            trace_file
            and os.path.exists(trace_file)
            and not args.quick
            and args.fault_start is None
            and args.fault_end is None
            and args.fault_step == 1
            and getattr(profile.fault_sweep, "sweep_strategy", "heuristic") != "exhaustive"
        )

        if use_heuristic:
            from write_trace_heuristic import (
                classify_trace,
                load_trace,
                summarize_classification,
            )

            trace = load_trace(trace_file)
            slot_ranges_for_heuristic: Dict[str, Tuple[int, int]] = {}
            flash_base = int(profile.memory.slots.get("exec", profile.memory.slots[list(profile.memory.slots.keys())[0]]).base) if profile.memory.slots else 0
            # Reconstruct slot ranges as bus addresses.
            for sname, sinfo in profile.memory.slots.items():
                slot_ranges_for_heuristic[sname] = (sinfo.base, sinfo.base + sinfo.size)
            # The flash_base for heuristic is the FlashBaseAddress of the NVMC.
            # In our platform, nvm starts at the exec slot base.
            flash_base = min(s.base for s in profile.memory.slots.values())

            fault_points = classify_trace(
                trace=trace,
                slot_ranges=slot_ranges_for_heuristic,
                flash_base=flash_base,
                page_size=getattr(profile.memory, "page_size", 4096),
            )
            heuristic_summary = summarize_classification(
                trace=trace,
                fault_points=fault_points,
                slot_ranges=slot_ranges_for_heuristic,
                flash_base=flash_base,
            )
            print(
                "Heuristic: {} fault points from {} writes (reduction {:.1f}x). "
                "Trailer writes: {}.".format(
                    heuristic_summary["selected_fault_points"],
                    heuristic_summary["total_writes"],
                    1.0 / max(heuristic_summary["reduction_ratio"], 0.001),
                    heuristic_summary["trailer_writes"],
                ),
                file=sys.stderr,
            )
        else:
            step = max(1, args.fault_step)
            fp_start = args.fault_start if args.fault_start is not None else 0
            fp_end = args.fault_end if args.fault_end is not None else max_writes
            fault_points = list(range(fp_start, fp_end, step))
            if max_writes - 1 not in fault_points and args.fault_end is None:
                fault_points.append(max_writes - 1)

        if args.quick:
            fault_points = quick_subset(fault_points)

        # Build combined write + erase fault point list.
        # Each fault point has a type ('w' for write, 'e' for erase).
        fault_types_list: Optional[List[str]] = None
        if include_erases and total_erases > 0:
            # Add erase fault points alongside write fault points.
            write_fps = [(fp, 'w') for fp in fault_points]
            erase_fps = list(range(0, total_erases))
            if args.quick:
                erase_fps = quick_subset(erase_fps)
            erase_typed = [(ep, 'e') for ep in erase_fps]
            combined = write_fps + erase_typed
            fault_points = [fp for fp, _ in combined]
            fault_types_list = [ft for _, ft in combined]
            print(
                "Running {} fault points ({} writes + {} erases) for '{}'...".format(
                    len(fault_points),
                    len(write_fps),
                    len(erase_typed),
                    profile.name,
                ),
                file=sys.stderr,
            )
        else:
            print(
                "Running {} fault points for '{}'...".format(len(fault_points), profile.name),
                file=sys.stderr,
            )

        # -------------------------------------------------------------------
        # Fault sweep (dispatch based on scenario)
        # -------------------------------------------------------------------
        if profile.scenario in ("resilient", "vulnerable"):
            sweep_results = run_classic_sweep(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                profile=profile,
                fault_points=fault_points,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
            )
        else:
            sweep_results = run_runtime_sweep(
                repo_root=repo_root,
                renode_test=renode_test,
                robot_suite=robot_suite,
                profile=profile,
                fault_points=fault_points,
                robot_vars=robot_vars,
                work_dir=work_dir,
                renode_remote_server_dir=args.renode_remote_server_dir,
                include_control=not args.no_control,
                num_workers=args.workers,
                trace_file=trace_file if not args.no_trace_replay else None,
                erase_trace_file=erase_trace_file if not args.no_trace_replay else None,
                fault_types_list=fault_types_list,
            )

        sweep_summary = summarize_runtime_sweep(
            sweep_results, total_writes=max_writes, profile=profile
        )

        # -------------------------------------------------------------------
        # State fuzzer (opt-in)
        # -------------------------------------------------------------------
        state_fuzz_results: Optional[List[Dict[str, Any]]] = None
        state_fuzz_summary: Optional[Dict[str, Any]] = None

        if profile.state_fuzzer.enabled:
            print("State fuzzer enabled (model={}), running...".format(
                profile.state_fuzzer.metadata_model
            ), file=sys.stderr)
            # State fuzzer runs via audit.robot / run_state_fuzz_point.resc
            # using the existing state_fuzzer.py to generate scenarios.
            # This is the opt-in plugin path. For now, mark as placeholder.
            state_fuzz_results = []
            state_fuzz_summary = {"status": "not_yet_wired", "metadata_model": profile.state_fuzzer.metadata_model}

        # -------------------------------------------------------------------
        # Verdict
        # -------------------------------------------------------------------
        brick_rate = sweep_summary["brick_rate"]
        found_issues = sweep_summary["bricks"] > 0

        verdict = "PASS"
        if profile.expect.should_find_issues and not found_issues:
            verdict = "FAIL — expected to find bricks but found none"
        elif not profile.expect.should_find_issues and found_issues:
            verdict = "FAIL — expected no bricks but found {} ({:.1%})".format(
                sweep_summary["bricks"], brick_rate
            )
        elif profile.expect.should_find_issues and brick_rate < profile.expect.brick_rate_min:
            verdict = "FAIL — brick rate {:.1%} below expected minimum {:.1%}".format(
                brick_rate, profile.expect.brick_rate_min
            )

        # -------------------------------------------------------------------
        # Build output
        # -------------------------------------------------------------------
        if Path(sys.argv[0]).suffix == ".py":
            command_parts = ["python3"] + sys.argv
        else:
            command_parts = sys.argv

        payload: Dict[str, Any] = {
            "engine": "renode-test",
            "profile": profile.name,
            "profile_path": str(profile.profile_path) if profile.profile_path else None,
            "schema_version": profile.schema_version,
            "calibrated_writes": max_writes,
            "calibrated_erases": total_erases,
            "fault_points_tested": len(fault_points),
            "quick": bool(args.quick),
            "heuristic": heuristic_summary,
            "verdict": verdict,
            "summary": {
                "runtime_sweep": sweep_summary,
            },
            "expect": {
                "should_find_issues": profile.expect.should_find_issues,
                "brick_rate_min": profile.expect.brick_rate_min,
            },
            "runtime_sweep_results": sweep_results,
            "execution": {
                "run_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "campaign_command": " ".join(shlex.quote(a) for a in command_parts),
                "artifacts_dir": report_artifacts_dir,
                "workers": args.workers,
            },
            "git": git_metadata(repo_root),
        }

        if state_fuzz_results is not None:
            payload["state_fuzz_results"] = state_fuzz_results
            payload["summary"]["state_fuzz"] = state_fuzz_summary

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

        # Print summary.
        print(json.dumps({
            "profile": profile.name,
            "verdict": verdict,
            "summary": payload["summary"],
        }, indent=2, sort_keys=True))

        # -------------------------------------------------------------------
        # Assertions
        # -------------------------------------------------------------------
        control_assert = (not args.no_control) and (not args.no_assert_control_boots)
        if control_assert and "control" in sweep_summary:
            ctrl = sweep_summary["control"]
            if ctrl.get("boot_outcome") != "success":
                print(
                    "ASSERTION FAILED: control point did not boot (outcome={})".format(
                        ctrl.get("boot_outcome")
                    ),
                    file=sys.stderr,
                )
                return EXIT_ASSERTION_FAILURE

        if verdict.startswith("FAIL"):
            return EXIT_ASSERTION_FAILURE

        return 0

    except Exception as exc:
        print("INFRASTRUCTURE FAILURE: {}".format(exc), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return EXIT_INFRA_FAILURE
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
