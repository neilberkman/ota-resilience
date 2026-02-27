#!/usr/bin/env python3
"""Run exploratory profile matrix and cluster anomalies.

This script is discovery-oriented: it generates profile variants from baseline
profiles, runs `audit_bootloader.py`, and clusters non-success outcomes across
the matrix. It is designed to surface candidate bug classes without assuming
specific known defects.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import fnmatch
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml


FAULT_PRESETS = ("profile", "write_erase", "write_erase_bit")
CRITERIA_PRESETS = ("profile", "vtor_any", "image_hash_exec")
ERASE_FAULT_TYPES = {"interrupted_erase", "multi_sector_atomicity"}
HARD_OUTCOMES = {"no_boot", "hard_fault"}


@dataclass
class MatrixCase:
    case_id: str
    base_profile_path: Path
    base_profile_name: str
    variant_profile_path: Path
    report_path: Path
    fault_preset: str
    criteria_preset: str
    expected_control_outcome: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run exploratory profile matrix and anomaly clustering."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Repository root path.",
    )
    parser.add_argument(
        "--renode-test",
        default=os.environ.get("RENODE_TEST", "renode-test"),
        help="Path to renode-test binary.",
    )
    parser.add_argument(
        "--renode-remote-server-dir",
        default=os.environ.get("RENODE_REMOTE_SERVER_DIR", ""),
        help="Path to Renode remote server directory.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Output directory. Default: "
            "results/exploratory/<UTC timestamp>-esp-idf-matrix"
        ),
    )
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help=(
            "Base profile path (relative to repo root) or glob. "
            "Can be repeated. Default is baseline ESP-IDF set."
        ),
    )
    parser.add_argument(
        "--include-defect-profiles",
        action="store_true",
        help="Also include esp_idf_fault_* profiles in discovery matrix.",
    )
    parser.add_argument(
        "--fault-preset",
        action="append",
        choices=FAULT_PRESETS,
        default=[],
        help=(
            "Fault preset to apply. Can be repeated. "
            "Default: profile + write_erase_bit."
        ),
    )
    parser.add_argument(
        "--criteria-preset",
        action="append",
        choices=CRITERIA_PRESETS,
        default=[],
        help=(
            "Success-criteria preset to apply. Can be repeated. "
            "Default: profile + image_hash_exec."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run audit with --quick.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Workers passed to audit_bootloader.py when not quick (default: 1).",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Optional case cap for incremental runs (0 = no cap).",
    )
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Skip execution for cases with existing report JSON.",
    )
    parser.add_argument(
        "--bounded-step-limit",
        default="0x180000",
        help="Step limit used for bit-corruption presets.",
    )
    parser.add_argument(
        "--top-clusters",
        type=int,
        default=25,
        help="Number of top clusters in markdown summary.",
    )
    return parser.parse_args()


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def default_profile_patterns(include_defects: bool) -> List[str]:
    base = [
        "profiles/esp_idf_ota_upgrade.yaml",
        "profiles/esp_idf_ota_rollback.yaml",
        "profiles/esp_idf_ota_no_rollback.yaml",
        "profiles/esp_idf_ota_crc_guard.yaml",
    ]
    if include_defects:
        base.append("profiles/esp_idf_fault_*.yaml")
    return base


def expand_profile_patterns(repo_root: Path, patterns: Sequence[str]) -> List[Path]:
    profiles_dir = repo_root / "profiles"
    all_profiles = sorted(profiles_dir.glob("*.yaml"))
    all_rel = [p.relative_to(repo_root).as_posix() for p in all_profiles]
    matches: List[Path] = []
    seen = set()
    for pat in patterns:
        # Exact path first.
        candidate = repo_root / pat
        if candidate.exists():
            key = candidate.resolve().as_posix()
            if key not in seen:
                seen.add(key)
                matches.append(candidate)
            continue
        # Glob on repo-relative paths.
        matched_any = False
        for rel, abs_path in zip(all_rel, all_profiles):
            if fnmatch.fnmatch(rel, pat):
                matched_any = True
                key = abs_path.resolve().as_posix()
                if key not in seen:
                    seen.add(key)
                    matches.append(abs_path)
        if not matched_any:
            print(
                "warning: profile pattern matched nothing: {}".format(pat),
                file=sys.stderr,
            )
    return sorted(matches)


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Profile is not a YAML mapping: {}".format(path))
    return data


def sanitize_name(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("_", "-"):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def apply_fault_preset(
    profile_doc: Dict[str, Any],
    preset: str,
    bounded_step_limit: int,
) -> None:
    if preset == "profile":
        return
    fs = profile_doc.setdefault("fault_sweep", {})
    if preset == "write_erase":
        fs["fault_types"] = ["power_loss", "interrupted_erase"]
    elif preset == "write_erase_bit":
        fs["fault_types"] = ["power_loss", "interrupted_erase", "bit_corruption"]
        fs["max_step_limit"] = bounded_step_limit
    else:
        raise ValueError("Unknown fault preset: {}".format(preset))


def apply_criteria_preset(profile_doc: Dict[str, Any], preset: str) -> None:
    if preset == "profile":
        return
    sc = profile_doc.setdefault("success_criteria", {})
    if preset == "vtor_any":
        sc.clear()
        sc["vtor_in_slot"] = "any"
        return
    if preset == "image_hash_exec":
        sc.clear()
        sc["vtor_in_slot"] = "any"
        sc["image_hash"] = True
        sc["image_hash_slot"] = "exec"
        expected = "staging" if "staging" in profile_doc.get("images", {}) else "exec"
        sc["expected_image"] = expected
        return
    raise ValueError("Unknown criteria preset: {}".format(preset))


def expected_control_outcome(profile_doc: Dict[str, Any]) -> str:
    expect = profile_doc.get("expect", {})
    if isinstance(expect, dict):
        return str(expect.get("control_outcome", "success"))
    return "success"


def build_matrix_cases(
    repo_root: Path,
    base_profiles: Sequence[Path],
    fault_presets: Sequence[str],
    criteria_presets: Sequence[str],
    bounded_step_limit: int,
    output_dir: Path,
    max_cases: int,
) -> List[MatrixCase]:
    temp_profiles_dir = output_dir / "profiles"
    temp_profiles_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    cases: List[MatrixCase] = []
    for base_path in base_profiles:
        base_doc = load_yaml(base_path)
        base_name = str(base_doc.get("name", base_path.stem))
        for fp in fault_presets:
            for cp in criteria_presets:
                variant = copy.deepcopy(base_doc)
                apply_fault_preset(variant, fp, bounded_step_limit)
                apply_criteria_preset(variant, cp)
                variant_name = "{}__f_{}__c_{}".format(base_name, fp, cp)
                variant["name"] = sanitize_name(variant_name)
                variant["skip_self_test"] = True
                case_id = sanitize_name(variant_name)
                variant_path = temp_profiles_dir / "{}.yaml".format(case_id)
                report_path = reports_dir / "{}.json".format(case_id)
                with variant_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(variant, f, sort_keys=False)
                cases.append(
                    MatrixCase(
                        case_id=case_id,
                        base_profile_path=base_path,
                        base_profile_name=base_name,
                        variant_profile_path=variant_path,
                        report_path=report_path,
                        fault_preset=fp,
                        criteria_preset=cp,
                        expected_control_outcome=expected_control_outcome(variant),
                    )
                )
                if max_cases > 0 and len(cases) >= max_cases:
                    return cases
    return cases


def run_case(
    repo_root: Path,
    renode_test: str,
    renode_remote_server_dir: str,
    case: MatrixCase,
    quick: bool,
    workers: int,
    reuse_existing: bool,
) -> Dict[str, Any]:
    if reuse_existing and case.report_path.exists():
        return {
            "case_id": case.case_id,
            "status": "reused",
            "exit_code": 0,
            "report_path": case.report_path.as_posix(),
        }

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_bootloader.py"),
        "--profile",
        str(case.variant_profile_path),
        "--output",
        str(case.report_path),
        "--renode-test",
        renode_test,
    ]
    if renode_remote_server_dir:
        cmd.extend(["--renode-remote-server-dir", renode_remote_server_dir])
    if quick:
        cmd.append("--quick")
    elif workers > 1:
        cmd.extend(["--workers", str(workers)])

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    result = {
        "case_id": case.case_id,
        "status": "ok" if proc.returncode == 0 else "nonzero_exit",
        "exit_code": proc.returncode,
        "report_path": case.report_path.as_posix(),
        "command": cmd,
    }
    if proc.stdout:
        result["stdout_tail"] = proc.stdout[-2000:]
    if proc.stderr:
        result["stderr_tail"] = proc.stderr[-2000:]
    return result


def load_report(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


def phase_bucket(fault_at: int, total: int) -> str:
    if total <= 1:
        return "single"
    pct = float(fault_at) / float(max(total - 1, 1))
    if pct < 0.33:
        return "early"
    if pct < 0.66:
        return "mid"
    return "late"


def severity_for_outcome(outcome: str, control_mismatch: bool) -> int:
    if control_mismatch:
        return 4
    if outcome in HARD_OUTCOMES:
        return 3
    if outcome in ("wrong_image", "wrong_pc"):
        return 2
    return 1


def extract_anomalies(
    cases: Sequence[MatrixCase],
    run_records: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    case_by_id = {c.case_id: c for c in cases}
    clusters: Dict[Tuple[str, ...], Dict[str, Any]] = {}

    totals = {
        "cases_total": len(cases),
        "cases_with_report": 0,
        "cases_missing_report": 0,
        "cases_control_mismatch": 0,
        "anomalous_points_total": 0,
    }

    for rr in run_records:
        case_id = rr.get("case_id")
        case = case_by_id.get(case_id)
        if case is None:
            continue
        report = load_report(Path(rr.get("report_path", "")))
        if report is None:
            totals["cases_missing_report"] += 1
            continue
        totals["cases_with_report"] += 1

        summary = report.get("summary", {})
        sweep = summary.get("runtime_sweep", {})
        control = sweep.get("control", {}) if isinstance(sweep, dict) else {}
        control_outcome = str(control.get("boot_outcome", "unknown"))
        control_slot = str(control.get("boot_slot", "none"))
        expected_control = case.expected_control_outcome

        if control_outcome != expected_control:
            totals["cases_control_mismatch"] += 1
            key = (
                "control_mismatch",
                control_outcome,
                control_slot,
                expected_control,
            )
            entry = clusters.setdefault(
                key,
                {
                    "kind": "control_mismatch",
                    "signature": {
                        "actual_control_outcome": control_outcome,
                        "actual_control_slot": control_slot,
                        "expected_control_outcome": expected_control,
                    },
                    "count": 0,
                    "case_ids": set(),
                    "base_profiles": set(),
                    "severity": severity_for_outcome(control_outcome, True),
                },
            )
            entry["count"] += 1
            entry["case_ids"].add(case_id)
            entry["base_profiles"].add(case.base_profile_name)

        points = report.get("runtime_sweep_results", [])
        if not isinstance(points, list):
            points = []
        calibrated_writes = int(report.get("calibrated_writes", 0) or 0)
        calibrated_erases = int(report.get("calibrated_erases", 0) or 0)

        for p in points:
            if not isinstance(p, dict):
                continue
            if p.get("is_control", False):
                continue
            if not p.get("fault_injected", False):
                continue
            outcome = str(p.get("boot_outcome", "unknown"))
            if outcome == "success":
                continue
            fault_type = str(p.get("fault_type", "w"))
            fault_at = int(p.get("fault_at", 0) or 0)
            boot_slot = str(p.get("boot_slot", "none"))
            signals = p.get("signals", {}) if isinstance(p.get("signals"), dict) else {}
            image_hash_match = str(signals.get("image_hash_match", "na"))
            total = calibrated_erases if fault_type in ("e", "a") else calibrated_writes
            phase = phase_bucket(fault_at, max(total, 1))

            key = (
                "fault_anomaly",
                outcome,
                fault_type,
                phase,
                boot_slot,
                image_hash_match,
            )
            entry = clusters.setdefault(
                key,
                {
                    "kind": "fault_anomaly",
                    "signature": {
                        "outcome": outcome,
                        "fault_type": fault_type,
                        "phase": phase,
                        "boot_slot": boot_slot,
                        "image_hash_match": image_hash_match,
                    },
                    "count": 0,
                    "case_ids": set(),
                    "base_profiles": set(),
                    "severity": severity_for_outcome(outcome, False),
                },
            )
            entry["count"] += 1
            entry["case_ids"].add(case_id)
            entry["base_profiles"].add(case.base_profile_name)
            totals["anomalous_points_total"] += 1

    cluster_rows: List[Dict[str, Any]] = []
    for entry in clusters.values():
        case_count = len(entry["case_ids"])
        profile_count = len(entry["base_profiles"])
        occurrence_count = int(entry["count"])
        novelty = 1.0 / float(max(profile_count, 1))
        reproducibility = float(case_count)
        severity = float(entry["severity"])
        score = severity * reproducibility * novelty * math.log1p(occurrence_count)
        cluster_rows.append(
            {
                "kind": entry["kind"],
                "signature": entry["signature"],
                "count": occurrence_count,
                "case_count": case_count,
                "profile_count": profile_count,
                "severity": entry["severity"],
                "score": round(score, 6),
                "case_ids": sorted(entry["case_ids"]),
                "base_profiles": sorted(entry["base_profiles"]),
            }
        )
    cluster_rows.sort(
        key=lambda x: (x["score"], x["severity"], x["case_count"], x["count"]),
        reverse=True,
    )
    return cluster_rows, totals


def render_markdown_summary(
    output_dir: Path,
    cases: Sequence[MatrixCase],
    runs: Sequence[Dict[str, Any]],
    clusters: Sequence[Dict[str, Any]],
    totals: Dict[str, Any],
    top_n: int,
) -> str:
    lines: List[str] = []
    lines.append("# Exploratory Matrix Summary")
    lines.append("")
    lines.append("- Generated: `{}`".format(utc_stamp()))
    lines.append("- Output dir: `{}`".format(output_dir.as_posix()))
    lines.append("- Cases planned: `{}`".format(len(cases)))
    lines.append("- Cases with report: `{}`".format(totals.get("cases_with_report", 0)))
    lines.append("- Cases missing report: `{}`".format(totals.get("cases_missing_report", 0)))
    lines.append("- Control mismatches: `{}`".format(totals.get("cases_control_mismatch", 0)))
    lines.append("- Anomalous fault points: `{}`".format(totals.get("anomalous_points_total", 0)))
    lines.append("")
    lines.append("## Top Clusters")
    lines.append("")
    if not clusters:
        lines.append("No anomalies detected.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Rank | Score | Kind | Signature | Occurrences | Cases | Profiles |")
    lines.append("| --- | ---: | --- | --- | ---: | ---: | ---: |")
    for idx, c in enumerate(clusters[:top_n], 1):
        sig = json.dumps(c["signature"], sort_keys=True)
        if len(sig) > 120:
            sig = sig[:117] + "..."
        lines.append(
            "| {} | {:.3f} | {} | `{}` | {} | {} | {} |".format(
                idx,
                float(c["score"]),
                c["kind"],
                sig,
                c["count"],
                c["case_count"],
                c["profile_count"],
            )
        )
    lines.append("")
    lines.append("## Run Records")
    lines.append("")
    lines.append("| Case | Status | Exit | Report |")
    lines.append("| --- | --- | ---: | --- |")
    for rr in runs:
        lines.append(
            "| `{}` | {} | {} | `{}` |".format(
                rr.get("case_id", "?"),
                rr.get("status", "?"),
                rr.get("exit_code", "?"),
                rr.get("report_path", ""),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        print("repo root does not exist: {}".format(repo_root), file=sys.stderr)
        return 2

    ts = utc_stamp()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else (repo_root / "results" / "exploratory" / ("{}-esp-idf-matrix".format(ts)))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    profile_patterns = args.profile or default_profile_patterns(args.include_defect_profiles)
    base_profiles = expand_profile_patterns(repo_root, profile_patterns)
    if not base_profiles:
        print("no base profiles found for patterns: {}".format(profile_patterns), file=sys.stderr)
        return 2

    fault_presets = args.fault_preset or ["profile", "write_erase_bit"]
    criteria_presets = args.criteria_preset or ["profile", "image_hash_exec"]
    bounded_step_limit = int(str(args.bounded_step_limit), 0)

    cases = build_matrix_cases(
        repo_root=repo_root,
        base_profiles=base_profiles,
        fault_presets=fault_presets,
        criteria_presets=criteria_presets,
        bounded_step_limit=bounded_step_limit,
        output_dir=output_dir,
        max_cases=args.max_cases,
    )

    print(
        "Exploratory matrix: {} base profiles, {} cases".format(
            len(base_profiles), len(cases)
        ),
        file=sys.stderr,
    )

    run_records: List[Dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        print(
            "[{}/{}] {}".format(i, len(cases), case.case_id),
            file=sys.stderr,
        )
        rr = run_case(
            repo_root=repo_root,
            renode_test=args.renode_test,
            renode_remote_server_dir=args.renode_remote_server_dir,
            case=case,
            quick=args.quick,
            workers=args.workers,
            reuse_existing=args.reuse_existing,
        )
        run_records.append(rr)

    clusters, totals = extract_anomalies(cases, run_records)

    matrix_payload = {
        "generated_at_utc": ts,
        "repo_root": repo_root.as_posix(),
        "output_dir": output_dir.as_posix(),
        "config": {
            "profile_patterns": profile_patterns,
            "fault_presets": fault_presets,
            "criteria_presets": criteria_presets,
            "quick": bool(args.quick),
            "workers": int(args.workers),
            "max_cases": int(args.max_cases),
            "reuse_existing": bool(args.reuse_existing),
            "bounded_step_limit": int(bounded_step_limit),
        },
        "cases": [
            {
                "case_id": c.case_id,
                "base_profile_name": c.base_profile_name,
                "base_profile_path": c.base_profile_path.relative_to(repo_root).as_posix(),
                "variant_profile_path": c.variant_profile_path.as_posix(),
                "report_path": c.report_path.as_posix(),
                "fault_preset": c.fault_preset,
                "criteria_preset": c.criteria_preset,
                "expected_control_outcome": c.expected_control_outcome,
            }
            for c in cases
        ],
        "runs": run_records,
        "totals": totals,
        "clusters": clusters,
    }

    matrix_json = output_dir / "matrix_results.json"
    matrix_json.write_text(
        json.dumps(matrix_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    md = render_markdown_summary(
        output_dir=output_dir,
        cases=cases,
        runs=run_records,
        clusters=clusters,
        totals=totals,
        top_n=args.top_clusters,
    )
    summary_md = output_dir / "anomaly_summary.md"
    summary_md.write_text(md, encoding="utf-8")

    print(
        json.dumps(
            {
                "output_dir": output_dir.as_posix(),
                "matrix_results": matrix_json.as_posix(),
                "summary": summary_md.as_posix(),
                "cases": len(cases),
                "clusters": len(clusters),
                "control_mismatches": totals.get("cases_control_mismatch", 0),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
