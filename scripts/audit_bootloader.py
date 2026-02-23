#!/usr/bin/env python3
"""Unguided bootloader resilience audit.

Given a bootloader ELF and platform description, systematically explores the
state x fault space to find conditions under which the bootloader bricks.
Reports invariant violations as potential bugs.

This is the primary tool for gaining confidence that an OTA update implementation
is safe against power-loss failures.

Usage:
    # Audit the built-in resilient bootloader:
    python3 scripts/audit_bootloader.py \
        --bootloader-elf examples/resilient_ota/bootloader.elf \
        --output results/audit_report.json

    # Audit MCUboot with nRF52840 layout:
    python3 scripts/audit_bootloader.py \
        --bootloader-elf results/oss_validation/assets/oss_mcuboot_mcuboot_swap_current_guard.elf \
        --platform platforms/nrf52840_nvmc_psel.repl \
        --slot-a-image results/oss_validation/assets/zephyr_slot0_padded.bin \
        --slot-b-image results/oss_validation/assets/zephyr_slot1_padded.bin \
        --output results/mcuboot_audit.json

    # Quick smoke test (3 fault points per scenario):
    python3 scripts/audit_bootloader.py --quick --output /tmp/smoke.json

    # Parallel execution (8 workers):
    python3 scripts/audit_bootloader.py --workers 8 --output results/audit.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Sibling imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fault_inject import FaultResult
from invariants import InvariantViolation, default_invariants, run_invariants
from state_fuzzer import (
    BootOutcome,
    FuzzScenario,
    SlotState,
    build_metadata_blob,
    build_slot_vectors,
    expected_outcome,
    generate_scenarios,
)

DEFAULT_RENODE_TEST = os.environ.get("RENODE_TEST", "renode-test")
ROBOT_SUITE = "tests/audit.robot"


# ---------------------------------------------------------------------------
# Scenario materialization (write binary blobs to disk for Renode)
# ---------------------------------------------------------------------------

def materialize_scenario(
    scenario: FuzzScenario,
    work_dir: Path,
    scenario_idx: int,
) -> Dict[str, str]:
    """Write fuzz scenario state to temp files and return Robot variable dict."""
    sdir = work_dir / "scenario_{}".format(scenario_idx)
    sdir.mkdir(parents=True, exist_ok=True)

    robot_vars: Dict[str, str] = {}

    # Metadata replicas.
    from state_fuzzer import build_metadata_blob, BOOT_META_REPLICA_SIZE  # noqa: F811
    r0_blob = build_metadata_blob(scenario.replica0)
    r0_path = sdir / "replica0.bin"
    r0_path.write_bytes(r0_blob)
    robot_vars["REPLICA0_FILE"] = str(r0_path)

    r1_blob = build_metadata_blob(scenario.replica1)
    r1_path = sdir / "replica1.bin"
    r1_path.write_bytes(r1_blob)
    robot_vars["REPLICA1_FILE"] = str(r1_path)

    # Slot vectors.
    from state_fuzzer import SLOT_A_BASE, SLOT_B_BASE  # noqa: F811
    slot_a_vec = build_slot_vectors(scenario.slot_a, SLOT_A_BASE)
    va_path = sdir / "slot_a_vec.bin"
    va_path.write_bytes(slot_a_vec)
    robot_vars["SLOT_A_VEC_FILE"] = str(va_path)

    slot_b_vec = build_slot_vectors(scenario.slot_b, SLOT_B_BASE)
    vb_path = sdir / "slot_b_vec.bin"
    vb_path.write_bytes(slot_b_vec)
    robot_vars["SLOT_B_VEC_FILE"] = str(vb_path)

    return robot_vars


# ---------------------------------------------------------------------------
# Single audit point execution
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AuditPoint:
    """One scenario + fault combination to test."""
    scenario_idx: int
    scenario: FuzzScenario
    fault_at: int
    fault_phase: str
    expected: BootOutcome


@dataclasses.dataclass
class AuditResult:
    """Result from one audit point, including invariant violations."""
    point: AuditPoint
    actual_outcome: str
    actual_boot_slot: Optional[str]
    matches_oracle: bool
    violations: List[Dict[str, Any]]
    pre_state: Dict[str, Any]
    post_state: Dict[str, Any]
    fault_diagnostics: Dict[str, Any]
    error: Optional[str] = None


def run_audit_point(
    repo_root: Path,
    renode_test: str,
    point: AuditPoint,
    work_dir: Path,
    robot_vars: List[str],
    scenario_files: Dict[str, str],
    renode_remote_server_dir: str,
) -> AuditResult:
    """Execute a single audit point and return the result."""
    point_dir = work_dir / "s{}_f{}".format(point.scenario_idx, point.fault_at)
    point_dir.mkdir(parents=True, exist_ok=True)

    result_file = point_dir / "result.json"
    rf_results = point_dir / "robot"
    bundle_dir = work_dir / ".dotnet_bundle"
    renode_config = work_dir / "renode.config"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        renode_test,
        "--renode-config", str(renode_config),
        str(repo_root / ROBOT_SUITE),
        "--results-dir", str(rf_results),
        "--variable", "RESULT_FILE:{}".format(result_file),
        "--variable", "FAULT_AT:{}".format(point.fault_at),
        "--variable", "FAULT_PHASE:{}".format(point.fault_phase),
        "--variable", "SCENARIO_ID:{}".format(point.scenario_idx),
    ]

    # Scenario-specific state files.
    for key, value in scenario_files.items():
        cmd.extend(["--variable", "{}:{}".format(key, value)])

    # Pass-through robot vars from CLI.
    for rv in robot_vars:
        cmd.extend(["--variable", rv])

    if renode_remote_server_dir:
        cmd.extend(["--robot-framework-remote-server-full-directory", renode_remote_server_dir])

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

    if proc.returncode != 0 or not result_file.exists():
        return AuditResult(
            point=point,
            actual_outcome="infra_error",
            actual_boot_slot=None,
            matches_oracle=False,
            violations=[],
            pre_state={},
            post_state={},
            fault_diagnostics={},
            error="renode-test rc={}\nSTDOUT:\n{}\nSTDERR:\n{}".format(
                proc.returncode,
                proc.stdout[-2000:] if proc.stdout else "",
                proc.stderr[-2000:] if proc.stderr else "",
            ),
        )

    data = json.loads(result_file.read_text(encoding="utf-8"))

    # Build FaultResult for invariant checking.
    fault_result = FaultResult(
        fault_at=point.fault_at,
        boot_outcome=data.get("boot_outcome", "unknown"),
        boot_slot=data.get("boot_slot"),
        nvm_state=data.get("nvm_state"),
        raw_log="",
        is_control=(point.fault_at < 0),
    )

    # Run invariants.
    pre_state = data.get("pre_state", {})
    violation_objs = run_invariants(
        fault_result,
        invariants=default_invariants("resilient"),
        pre_state=pre_state,
    )

    # Check oracle match.
    expected_boots = point.expected.boots
    expected_slot = point.expected.boot_slot
    actual_boots = (data.get("boot_outcome") == "success")
    actual_slot_str = data.get("boot_slot")
    actual_slot_int = {"A": 0, "B": 1}.get(actual_slot_str) if actual_slot_str else None

    if point.fault_at < 0:
        # No fault — oracle should match exactly.
        matches = (expected_boots == actual_boots)
        if matches and expected_boots and expected_slot is not None:
            matches = (expected_slot == actual_slot_int)
    else:
        # With fault — oracle was computed on the pre-fault state.
        # A resilient bootloader should still boot if the pre-state had valid slots.
        matches = (expected_boots == actual_boots) or (not expected_boots and not actual_boots)

    violations_dicts = [
        {
            "invariant": v.invariant_name,
            "description": v.description,
            "details": v.details,
        }
        for v in violation_objs
    ]

    return AuditResult(
        point=point,
        actual_outcome=data.get("boot_outcome", "unknown"),
        actual_boot_slot=actual_slot_str,
        matches_oracle=matches,
        violations=violations_dicts,
        pre_state=pre_state,
        post_state=data.get("post_state", {}),
        fault_diagnostics=data.get("fault_diagnostics", {}),
    )


# ---------------------------------------------------------------------------
# Audit campaign
# ---------------------------------------------------------------------------

def build_audit_points(
    scenarios: List[FuzzScenario],
    fault_points_per_scenario: List[int],
    fault_phase: str,
) -> List[AuditPoint]:
    """Generate the full matrix of (scenario, fault_point) combinations."""
    points: List[AuditPoint] = []
    for idx, scenario in enumerate(scenarios):
        outcome = expected_outcome(scenario)

        # Always include a no-fault control run for each scenario.
        points.append(AuditPoint(
            scenario_idx=idx,
            scenario=scenario,
            fault_at=-1,
            fault_phase="none",
            expected=outcome,
        ))

        # Fault points within the write phase.
        for fp in fault_points_per_scenario:
            points.append(AuditPoint(
                scenario_idx=idx,
                scenario=scenario,
                fault_at=fp,
                fault_phase=fault_phase,
                expected=outcome,
            ))

    return points


def run_audit_campaign(
    repo_root: Path,
    renode_test: str,
    scenarios: List[FuzzScenario],
    fault_points_per_scenario: List[int],
    fault_phase: str,
    robot_vars: List[str],
    work_dir: Path,
    renode_remote_server_dir: str,
    workers: int,
) -> List[AuditResult]:
    """Run the full audit campaign, optionally in parallel."""
    points = build_audit_points(scenarios, fault_points_per_scenario, fault_phase)

    # Pre-materialize all scenario files.
    scenario_file_cache: Dict[int, Dict[str, str]] = {}
    for idx, scenario in enumerate(scenarios):
        scenario_file_cache[idx] = materialize_scenario(scenario, work_dir, idx)

    results: List[AuditResult] = []
    total = len(points)

    def execute_point(point: AuditPoint) -> AuditResult:
        return run_audit_point(
            repo_root=repo_root,
            renode_test=renode_test,
            point=point,
            work_dir=work_dir,
            robot_vars=robot_vars,
            scenario_files=scenario_file_cache[point.scenario_idx],
            renode_remote_server_dir=renode_remote_server_dir,
        )

    if workers <= 1:
        for i, point in enumerate(points):
            print("\r  [{}/{}] scenario {} fault_at={}".format(
                i + 1, total, point.scenario_idx, point.fault_at
            ), end="", flush=True, file=sys.stderr)
            results.append(execute_point(point))
        print("", file=sys.stderr)
    else:
        completed = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all points.
            future_to_point = {
                executor.submit(execute_point, point): point
                for point in points
            }
            for future in concurrent.futures.as_completed(future_to_point):
                completed += 1
                point = future_to_point[future]
                print("\r  [{}/{}] scenario {} fault_at={}".format(
                    completed, total, point.scenario_idx, point.fault_at
                ), end="", flush=True, file=sys.stderr)
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(AuditResult(
                        point=point,
                        actual_outcome="infra_error",
                        actual_boot_slot=None,
                        matches_oracle=False,
                        violations=[],
                        pre_state={},
                        post_state={},
                        fault_diagnostics={},
                        error=str(e),
                    ))
        print("", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def summarize_audit(results: List[AuditResult]) -> Dict[str, Any]:
    """Build human-readable summary from audit results."""
    control_results = [r for r in results if r.point.fault_at < 0]
    faulted_results = [r for r in results if r.point.fault_at >= 0]
    errors = [r for r in results if r.error is not None]

    # Control run stats.
    control_boots = sum(1 for r in control_results if r.actual_outcome == "success")
    control_oracle_match = sum(1 for r in control_results if r.matches_oracle)

    # Faulted run stats.
    faulted_bricks = sum(1 for r in faulted_results if r.actual_outcome != "success")
    faulted_total = len(faulted_results)
    faulted_violations = sum(1 for r in faulted_results if r.violations)

    # Aggregate violations by type.
    violation_counts: Dict[str, int] = {}
    for r in results:
        for v in r.violations:
            name = v.get("invariant", "unknown")
            violation_counts[name] = violation_counts.get(name, 0) + 1

    # Find worst scenarios (most violations).
    scenario_violation_count: Dict[int, int] = {}
    for r in results:
        if r.violations:
            idx = r.point.scenario_idx
            scenario_violation_count[idx] = scenario_violation_count.get(idx, 0) + len(r.violations)
    worst_scenarios = sorted(scenario_violation_count.items(), key=lambda x: -x[1])[:5]

    return {
        "total_points": len(results),
        "control_runs": len(control_results),
        "control_boots": control_boots,
        "control_oracle_matches": control_oracle_match,
        "faulted_runs": faulted_total,
        "faulted_bricks": faulted_bricks,
        "faulted_brick_rate": (float(faulted_bricks) / faulted_total) if faulted_total else 0.0,
        "faulted_with_violations": faulted_violations,
        "infra_errors": len(errors),
        "violation_counts": violation_counts,
        "worst_scenarios": [
            {"scenario_idx": idx, "violation_count": count}
            for idx, count in worst_scenarios
        ],
        "verdict": _verdict(control_boots, len(control_results), faulted_bricks, faulted_total, faulted_violations),
    }


def _verdict(
    control_boots: int,
    control_total: int,
    faulted_bricks: int,
    faulted_total: int,
    faulted_violations: int,
) -> str:
    if control_total > 0 and control_boots < control_total:
        return "FAIL: {} of {} control runs did not boot (bootloader may be broken independent of faults)".format(
            control_total - control_boots, control_total
        )
    if faulted_violations > 0:
        return "FAIL: {} invariant violations across {} faulted runs — potential bugs found".format(
            faulted_violations, faulted_total
        )
    if faulted_bricks > 0 and faulted_total > 0:
        rate = 100.0 * faulted_bricks / faulted_total
        if rate > 50.0:
            return "FAIL: {:.1f}% brick rate ({}/{}) — bootloader is NOT resilient to power-loss".format(
                rate, faulted_bricks, faulted_total
            )
        return "WARN: {:.1f}% brick rate ({}/{}) — some fault scenarios cause bricks".format(
            rate, faulted_bricks, faulted_total
        )
    return "PASS: 0 bricks, 0 violations across {} faulted runs".format(faulted_total)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Unguided bootloader resilience audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--bootloader-elf", default="examples/resilient_ota/bootloader.elf")
    p.add_argument("--firmware-elf", default="", help="Optional application firmware ELF")
    p.add_argument("--platform", default="platforms/cortex_m0_nvm.repl")
    p.add_argument("--slot-a-image", default="", help="Slot A image file")
    p.add_argument("--slot-b-image", default="", help="Slot B image file")
    p.add_argument("--peripheral-includes", default="", help="Semicolon-separated C# peripheral files")
    p.add_argument("--output", required=True, help="Output JSON report path")

    # State space exploration.
    p.add_argument("--scenarios", type=int, default=50, help="Number of fuzz scenarios (default: 50)")
    p.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    p.add_argument("--fault-phase", choices=("slot_copy", "metadata", "none"), default="slot_copy")
    p.add_argument("--fault-range", default="0:28160", help="start:end for fault point range")
    p.add_argument("--fault-step", type=int, default=4000, help="Step between fault points")
    p.add_argument("--quick", action="store_true", help="Quick mode: 3 fault points, 10 scenarios")

    # Execution.
    p.add_argument("--workers", type=int, default=1, help="Parallel workers (default: 1)")
    p.add_argument("--renode-test", default=DEFAULT_RENODE_TEST)
    p.add_argument("--renode-remote-server-dir", default="")
    p.add_argument("--robot-var", action="append", default=[], metavar="KEY:VALUE")
    p.add_argument("--keep-artifacts", action="store_true")

    # Assertions.
    p.add_argument("--assert-no-bricks", action="store_true", help="Exit 1 if any faulted run bricks")
    p.add_argument("--assert-no-violations", action="store_true", help="Exit 1 if any invariant violation")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    temp_ctx: Optional[tempfile.TemporaryDirectory] = None

    try:
        # Resolve renode-test.
        renode_test = args.renode_test
        if not os.path.isabs(renode_test):
            resolved = shutil.which(renode_test)
            if resolved is None:
                print("ERROR: renode-test '{}' not found in PATH".format(renode_test), file=sys.stderr)
                return 2
            renode_test = resolved

        # Quick mode overrides.
        num_scenarios = args.scenarios
        fault_step = args.fault_step
        if args.quick:
            num_scenarios = min(num_scenarios, 10)
            fault_step = max(fault_step, 10000)

        # Generate scenarios.
        print("Generating {} fuzz scenarios (seed={})...".format(num_scenarios, args.seed), file=sys.stderr)
        scenarios = generate_scenarios(count=num_scenarios, seed=args.seed)

        # Build fault points.
        start_s, end_s = args.fault_range.split(":", 1)
        start, end = int(start_s), int(end_s)
        fault_points = list(range(start, end + 1, fault_step))
        if end not in fault_points:
            fault_points.append(end)
        if args.quick and len(fault_points) > 3:
            mid = fault_points[len(fault_points) // 2]
            fault_points = [fault_points[0], mid, fault_points[-1]]

        total_points = num_scenarios * (1 + len(fault_points))  # +1 for control
        print("Audit plan: {} scenarios x ({} fault points + 1 control) = {} total runs".format(
            num_scenarios, len(fault_points), total_points
        ), file=sys.stderr)

        # Work directory.
        if args.keep_artifacts:
            work_dir = repo_root / "results" / "audit_runs" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_ctx = tempfile.TemporaryDirectory(prefix="audit_bl_")
            work_dir = Path(temp_ctx.name)

        # Robot vars.
        robot_vars = [
            "PLATFORM_REPL:{}".format(str((repo_root / args.platform).resolve())),
            "BOOTLOADER_ELF:{}".format(str((repo_root / args.bootloader_elf).resolve())),
        ]
        if args.firmware_elf:
            robot_vars.append("FIRMWARE_ELF:{}".format(str((repo_root / args.firmware_elf).resolve())))
        if args.slot_a_image:
            robot_vars.append("SLOT_A_IMAGE_FILE:{}".format(str((repo_root / args.slot_a_image).resolve())))
        if args.slot_b_image:
            robot_vars.append("SLOT_B_IMAGE_FILE:{}".format(str((repo_root / args.slot_b_image).resolve())))
        if args.peripheral_includes:
            robot_vars.append("PERIPHERAL_INCLUDES:{}".format(args.peripheral_includes))
        for rv in args.robot_var:
            key, sep, value = rv.partition(":")
            if sep:
                robot_vars.append("{}:{}".format(key, value))

        # Run campaign.
        start_time = time.monotonic()
        print("Running audit...", file=sys.stderr)
        results = run_audit_campaign(
            repo_root=repo_root,
            renode_test=renode_test,
            scenarios=scenarios,
            fault_points_per_scenario=fault_points,
            fault_phase=args.fault_phase,
            robot_vars=robot_vars,
            work_dir=work_dir,
            renode_remote_server_dir=args.renode_remote_server_dir,
            workers=args.workers,
        )
        elapsed = time.monotonic() - start_time

        # Summarize.
        summary = summarize_audit(results)
        summary["elapsed_seconds"] = round(elapsed, 1)

        # Build output payload.
        payload = {
            "engine": "renode-test",
            "mode": "audit",
            "summary": summary,
            "config": {
                "scenarios": num_scenarios,
                "seed": args.seed,
                "fault_points": fault_points,
                "fault_phase": args.fault_phase,
                "workers": args.workers,
                "bootloader_elf": args.bootloader_elf,
                "platform": args.platform,
                "quick": args.quick,
            },
            "execution": {
                "run_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "elapsed_seconds": round(elapsed, 1),
            },
            "scenarios": [
                {
                    "idx": idx,
                    "description": s.description,
                    "expected_boots": expected_outcome(s).boots,
                    "expected_slot": expected_outcome(s).boot_slot,
                }
                for idx, s in enumerate(scenarios)
            ],
            "results": [
                {
                    "scenario_idx": r.point.scenario_idx,
                    "fault_at": r.point.fault_at,
                    "fault_phase": r.point.fault_phase,
                    "actual_outcome": r.actual_outcome,
                    "actual_boot_slot": r.actual_boot_slot,
                    "matches_oracle": r.matches_oracle,
                    "violations": r.violations,
                    "error": r.error,
                }
                for r in results
            ],
        }

        # Only include detailed state for interesting results (violations, bricks, oracle mismatches).
        interesting = [
            r for r in results
            if r.violations or r.actual_outcome != "success" or not r.matches_oracle or r.error
        ]
        if interesting:
            payload["interesting_results"] = [
                {
                    "scenario_idx": r.point.scenario_idx,
                    "scenario_description": r.point.scenario.description,
                    "fault_at": r.point.fault_at,
                    "fault_phase": r.point.fault_phase,
                    "expected": {
                        "boots": r.point.expected.boots,
                        "boot_slot": r.point.expected.boot_slot,
                        "reason": r.point.expected.reason,
                    },
                    "actual_outcome": r.actual_outcome,
                    "actual_boot_slot": r.actual_boot_slot,
                    "matches_oracle": r.matches_oracle,
                    "violations": r.violations,
                    "pre_state": r.pre_state,
                    "post_state": r.post_state,
                    "fault_diagnostics": r.fault_diagnostics,
                    "error": r.error,
                }
                for r in interesting
            ]

        # Write report.
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

        # Print summary.
        print("\n{}".format(summary["verdict"]), file=sys.stderr)
        print(json.dumps(summary, indent=2, sort_keys=True))

        # Assertions.
        exit_code = 0
        if args.assert_no_bricks and summary.get("faulted_bricks", 0) > 0:
            print("ASSERTION FAILED: --assert-no-bricks ({} bricks)".format(
                summary["faulted_bricks"]
            ), file=sys.stderr)
            exit_code = 1
        if args.assert_no_violations and summary.get("faulted_with_violations", 0) > 0:
            print("ASSERTION FAILED: --assert-no-violations ({} runs with violations)".format(
                summary["faulted_with_violations"]
            ), file=sys.stderr)
            exit_code = 1

        return exit_code

    except Exception as exc:
        print("INFRASTRUCTURE ERROR: {}".format(exc), file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 2
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
