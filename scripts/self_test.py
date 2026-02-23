#!/usr/bin/env python3
"""Self-test: validate that the audit tool detects known defects.

Runs audit_bootloader.py against each intentional-fault variant and the
correct resilient bootloader. Asserts:

  - Correct bootloader (bootloader_none): 0 bricks, 0 violations
  - Each defective variant: either bricks or invariant violations detected

This is the meta-test that proves the audit tool actually works. If the
tool can't distinguish a broken bootloader from a correct one, it's useless
for finding novel bugs.

Usage:
    python3 scripts/self_test.py --renode-test /path/to/renode-test

    # Quick smoke (fewer scenarios/fault points):
    python3 scripts/self_test.py --quick

    # Parallel (one audit per variant, each audit uses 1 worker internally):
    python3 scripts/self_test.py --parallel
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


VARIANTS = [
    # (name, elf_path, should_find_issues)
    ("none",                    "examples/fault_variants/bootloader_none.elf",                    False),
    ("no_fallback",             "examples/fault_variants/bootloader_no_fallback.elf",              True),
    ("no_vector_check",         "examples/fault_variants/bootloader_no_vector_check.elf",          True),
    ("both_replicas_race",      "examples/fault_variants/bootloader_both_replicas_race.elf",       True),
    ("crc_off_by_one",          "examples/fault_variants/bootloader_crc_off_by_one.elf",           True),
    ("seq_naive",               "examples/fault_variants/bootloader_seq_naive.elf",                True),
    ("no_boot_count",           "examples/fault_variants/bootloader_no_boot_count.elf",            True),
    ("geometry_last_sector",    "examples/fault_variants/bootloader_geometry_last_sector.elf",     True),
    ("security_counter_early",  "examples/fault_variants/bootloader_security_counter_early.elf",   True),
    ("wrong_erased_value",      "examples/fault_variants/bootloader_wrong_erased_value.elf",       True),
    ("trailer_wrong_offset",    "examples/fault_variants/bootloader_trailer_wrong_offset.elf",     True),
]


def run_audit_for_variant(
    repo_root: Path,
    name: str,
    elf_path: str,
    output_dir: Path,
    extra_args: List[str],
) -> Tuple[str, Dict[str, Any]]:
    """Run audit_bootloader.py for one variant and return (name, summary)."""
    output_file = output_dir / "{}_audit.json".format(name)

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_bootloader.py"),
        "--bootloader-elf", elf_path,
        "--output", str(output_file),
    ] + extra_args

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if not output_file.exists():
        return name, {
            "error": "audit did not produce output",
            "stdout": proc.stdout[-1000:] if proc.stdout else "",
            "stderr": proc.stderr[-1000:] if proc.stderr else "",
            "returncode": proc.returncode,
        }

    report = json.loads(output_file.read_text(encoding="utf-8"))
    return name, report.get("summary", {})


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-test: validate audit tool detects known defects")
    parser.add_argument("--renode-test", default=os.environ.get("RENODE_TEST", "renode-test"))
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer scenarios)")
    parser.add_argument("--parallel", action="store_true", help="Run variant audits in parallel")
    parser.add_argument("--output-dir", default="", help="Directory for audit reports (default: temp)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # Build extra args for audit_bootloader.py.
    extra_args = [
        "--renode-test", args.renode_test,
        "--seed", str(args.seed),
    ]
    if args.quick:
        extra_args.append("--quick")

    # Output directory.
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_ctx = None
    else:
        temp_ctx = tempfile.TemporaryDirectory(prefix="self_test_")
        output_dir = Path(temp_ctx.name)

    try:
        results: Dict[str, Dict[str, Any]] = {}
        print("Self-test: running audit against {} variants".format(len(VARIANTS)), file=sys.stderr)

        if args.parallel:
            with concurrent.futures.ProcessPoolExecutor(max_workers=len(VARIANTS)) as executor:
                futures = {
                    executor.submit(
                        run_audit_for_variant, repo_root, name, elf, output_dir, extra_args
                    ): (name, should_find)
                    for name, elf, should_find in VARIANTS
                }
                for future in concurrent.futures.as_completed(futures):
                    name, summary = future.result()
                    results[name] = summary
                    print("  {} done".format(name), file=sys.stderr)
        else:
            for name, elf, should_find in VARIANTS:
                print("  Running audit for {}...".format(name), file=sys.stderr, end="", flush=True)
                _, summary = run_audit_for_variant(repo_root, name, elf, output_dir, extra_args)
                results[name] = summary
                print(" done", file=sys.stderr)

        # Evaluate results.
        print("\n" + "=" * 70, file=sys.stderr)
        print("SELF-TEST RESULTS", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        passes = 0
        failures = 0
        errors = 0

        for name, elf, should_find_issues in VARIANTS:
            summary = results.get(name, {})

            if "error" in summary:
                status = "ERROR"
                detail = summary.get("error", "unknown error")
                errors += 1
            else:
                bricks = summary.get("faulted_bricks", 0)
                violations = summary.get("faulted_with_violations", 0)
                has_issues = (bricks > 0) or (violations > 0)

                if should_find_issues:
                    if has_issues:
                        status = "PASS"
                        detail = "detected: {} bricks, {} violations".format(bricks, violations)
                        passes += 1
                    else:
                        status = "FAIL"
                        detail = "defect NOT detected (0 bricks, 0 violations)"
                        failures += 1
                else:
                    if not has_issues:
                        status = "PASS"
                        detail = "correct: 0 bricks, 0 violations"
                        passes += 1
                    else:
                        status = "FAIL"
                        detail = "false positive: {} bricks, {} violations on correct bootloader".format(
                            bricks, violations
                        )
                        failures += 1

            verdict_str = summary.get("verdict", "")
            print("  [{:>5s}] {:30s} {}".format(status, name, detail), file=sys.stderr)
            if verdict_str:
                print("          verdict: {}".format(verdict_str), file=sys.stderr)

        print("=" * 70, file=sys.stderr)
        print("{} passed, {} failed, {} errors".format(passes, failures, errors), file=sys.stderr)

        # Write machine-readable summary.
        summary_file = output_dir / "self_test_summary.json"
        summary_data = {
            "total": len(VARIANTS),
            "passes": passes,
            "failures": failures,
            "errors": errors,
            "variants": {
                name: {
                    "elf": elf,
                    "should_find_issues": should_find,
                    "summary": results.get(name, {}),
                }
                for name, elf, should_find in VARIANTS
            },
        }
        summary_file.write_text(json.dumps(summary_data, indent=2, sort_keys=True), encoding="utf-8")
        print("\nDetailed reports in: {}".format(output_dir), file=sys.stderr)

        return 0 if (failures == 0 and errors == 0) else 1

    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
