#!/usr/bin/env python3
"""Run named external OSS validation profiles via ota_fault_campaign.py."""

from __future__ import annotations

import argparse
import copy
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_GENERIC_SUITE = "tests/generic_fault_point.robot"
DISALLOWED_LICENSE_TOKENS = ("gpl", "agpl", "commercial")
EXPECTATION_KEYS = (
    "bricks_min",
    "bricks_max",
    "brick_rate_min",
    "brick_rate_max",
    "require_control_success",
)


class SafeTemplateDict(dict):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OTA validation for external OSS firmware profiles.")
    parser.add_argument("--manifest", required=True, help="JSON file containing validation profiles")
    parser.add_argument("--profile", required=True, help="Profile name from manifest")
    parser.add_argument("--renode-test", required=True, help="Path or name of renode-test binary")
    parser.add_argument("--output")
    parser.add_argument("--allow-disallowed-licenses", action="store_true")
    return parser.parse_args()


def load_manifest(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "profiles" not in data or not isinstance(data["profiles"], list):
        raise ValueError("Manifest must be an object with a 'profiles' array")
    return data


def find_profile(data: Dict[str, Any], name: str) -> Dict[str, Any]:
    for profile in data["profiles"]:
        if isinstance(profile, dict) and profile.get("name") == name:
            return profile
    raise ValueError("Profile '{}' not found in manifest".format(name))


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def render_templates(value: Any, variables: Dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format_map(SafeTemplateDict(variables))
    if isinstance(value, list):
        return [render_templates(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: render_templates(v, variables) for k, v in value.items()}
    return value


def normalize_list_of_strings(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError("Field '{}' must be an array of strings".format(field_name))
    return list(value)


def validate_source_checkout(source: Any, field_name: str) -> None:
    if source is None:
        return
    if not isinstance(source, dict):
        raise ValueError("Field '{}' must be an object".format(field_name))
    if "repo" not in source or "ref" not in source:
        raise ValueError("Field '{}' must include 'repo' and 'ref'".format(field_name))
    if not isinstance(source["repo"], str) or not isinstance(source["ref"], str):
        raise ValueError("Field '{}.repo' and '{}.ref' must be strings".format(field_name, field_name))
    normalize_list_of_strings(source.get("revert_commits"), "{}.revert_commits".format(field_name))
    normalize_list_of_strings(source.get("cherry_pick_commits"), "{}.cherry_pick_commits".format(field_name))
    normalize_list_of_strings(source.get("apply_patches"), "{}.apply_patches".format(field_name))


def validate_expectations(expect: Any, field_name: str) -> None:
    if expect is None:
        return
    if not isinstance(expect, dict):
        raise ValueError("Field '{}' must be an object".format(field_name))

    unknown = sorted(set(expect.keys()) - set(EXPECTATION_KEYS))
    if unknown:
        raise ValueError(
            "Field '{}' contains unknown keys: {}. Allowed keys: {}".format(
                field_name,
                ", ".join(unknown),
                ", ".join(EXPECTATION_KEYS),
            )
        )

    for key in ("bricks_min", "bricks_max"):
        if key in expect:
            value = expect[key]
            if not isinstance(value, int) or value < 0:
                raise ValueError("Field '{}.{}' must be an integer >= 0".format(field_name, key))

    for key in ("brick_rate_min", "brick_rate_max"):
        if key in expect:
            value = expect[key]
            if not isinstance(value, (int, float)):
                raise ValueError("Field '{}.{}' must be a number".format(field_name, key))
            if value < 0.0 or value > 1.0:
                raise ValueError("Field '{}.{}' must be between 0.0 and 1.0".format(field_name, key))

    if "require_control_success" in expect and not isinstance(expect["require_control_success"], bool):
        raise ValueError("Field '{}.require_control_success' must be true/false".format(field_name))

    if "bricks_min" in expect and "bricks_max" in expect and expect["bricks_min"] > expect["bricks_max"]:
        raise ValueError("Field '{}': bricks_min cannot be greater than bricks_max".format(field_name))
    if "brick_rate_min" in expect and "brick_rate_max" in expect and expect["brick_rate_min"] > expect["brick_rate_max"]:
        raise ValueError("Field '{}': brick_rate_min cannot be greater than brick_rate_max".format(field_name))


def validate_profile(profile: Dict[str, Any], allow_disallowed_licenses: bool) -> None:
    required = ("name", "license", "fault_range", "fault_step", "total_writes", "robot_vars")
    missing = [k for k in required if k not in profile]
    if missing:
        raise ValueError("Profile '{}' is missing required fields: {}".format(profile.get("name"), ", ".join(missing)))

    if not isinstance(profile["robot_vars"], list) or not all(isinstance(v, str) for v in profile["robot_vars"]):
        raise ValueError("Profile '{}' field 'robot_vars' must be an array of KEY:VALUE strings".format(profile["name"]))

    normalize_list_of_strings(profile.get("campaign_args"), "campaign_args")
    normalize_list_of_strings(profile.get("setup_commands"), "setup_commands")
    validate_source_checkout(profile.get("source_checkout"), "source_checkout")
    validate_expectations(profile.get("expect"), "expect")

    license_name = str(profile["license"]).strip().lower()
    if not allow_disallowed_licenses and any(token in license_name for token in DISALLOWED_LICENSE_TOKENS):
        raise ValueError(
            "Profile '{}' uses disallowed license '{}'; allowed policy excludes GPL/AGPL/commercial".format(
                profile["name"], profile["license"]
            )
        )

    variants = profile.get("variants")
    if variants is None:
        return

    if not isinstance(variants, list) or not variants:
        raise ValueError("Field 'variants' must be a non-empty array")

    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            raise ValueError("variants[{}] must be an object".format(index))
        if "name" not in variant or not isinstance(variant["name"], str) or not variant["name"].strip():
            raise ValueError("variants[{}] must include a non-empty string 'name'".format(index))
        if "overrides" in variant and not isinstance(variant["overrides"], dict):
            raise ValueError("variants[{}].overrides must be an object".format(index))
        if "overrides" in variant:
            validate_expectations(variant["overrides"].get("expect"), "variants[{}].overrides.expect".format(index))
        validate_expectations(variant.get("expect"), "variants[{}].expect".format(index))
        normalize_list_of_strings(variant.get("setup_commands"), "variants[{}].setup_commands".format(index))
        validate_source_checkout(variant.get("source_checkout"), "variants[{}].source_checkout".format(index))


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def run_shell_commands(commands: Iterable[str], cwd: Path, variables: Dict[str, str]) -> None:
    for raw_command in commands:
        command = str(render_templates(raw_command, variables))
        print(">> {}".format(command))
        proc = subprocess.run(
            ["/bin/bash", "-lc", command],
            cwd=str(cwd),
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError("setup command failed (rc={}): {}".format(proc.returncode, command))


def prepare_source_checkout(
    repo_root: Path,
    source_checkout: Dict[str, Any] | None,
    variables: Dict[str, str],
) -> Tuple[tempfile.TemporaryDirectory[str] | None, Path | None]:
    if source_checkout is None:
        return None, None

    rendered = render_templates(source_checkout, variables)
    repo_path = resolve_path(repo_root, str(rendered["repo"]))
    ref = str(rendered["ref"])
    if not repo_path.exists():
        raise FileNotFoundError("source_checkout repo not found: {}".format(repo_path))

    temp_ctx: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="oss_src_")
    worktree_path = Path(temp_ctx.name) / "source"

    def fail(message: str) -> None:
        subprocess.run(["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)], check=False)
        temp_ctx.cleanup()
        raise RuntimeError(message)

    if rendered.get("fetch_remote"):
        remote = str(rendered.get("fetch_remote"))
        fetch_args: List[str] = ["git", "-C", str(repo_path), "fetch", remote]
        if rendered.get("fetch_depth") is not None:
            fetch_args.extend(["--depth", str(rendered["fetch_depth"])])
        if subprocess.run(fetch_args, check=False).returncode != 0:
            fail("failed to fetch source repo '{}' remote '{}'".format(repo_path, remote))

    if subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "add", "--detach", str(worktree_path), ref],
        check=False,
    ).returncode != 0:
        fail("failed to create worktree for {} at {}".format(ref, repo_path))

    for commit in normalize_list_of_strings(rendered.get("revert_commits"), "source_checkout.revert_commits"):
        if subprocess.run(
            ["git", "-C", str(worktree_path), "revert", "--no-edit", "--no-commit", commit],
            check=False,
        ).returncode != 0:
            fail("failed to revert commit '{}' in {}".format(commit, worktree_path))

    for commit in normalize_list_of_strings(rendered.get("cherry_pick_commits"), "source_checkout.cherry_pick_commits"):
        if subprocess.run(
            ["git", "-C", str(worktree_path), "cherry-pick", "--no-commit", commit],
            check=False,
        ).returncode != 0:
            fail("failed to cherry-pick commit '{}' in {}".format(commit, worktree_path))

    for patch in normalize_list_of_strings(rendered.get("apply_patches"), "source_checkout.apply_patches"):
        patch_path = resolve_path(repo_root, patch)
        if subprocess.run(["git", "-C", str(worktree_path), "apply", str(patch_path)], check=False).returncode != 0:
            fail("failed to apply patch '{}' in {}".format(patch_path, worktree_path))

    return temp_ctx, worktree_path


def cleanup_source_checkout(
    source_checkout: Dict[str, Any] | None,
    temp_ctx: tempfile.TemporaryDirectory[str] | None,
    worktree_path: Path | None,
    repo_root: Path,
    variables: Dict[str, str],
) -> None:
    if temp_ctx is None:
        return
    try:
        if source_checkout is not None and worktree_path is not None:
            rendered = render_templates(source_checkout, variables)
            repo_path = resolve_path(repo_root, str(rendered["repo"]))
            subprocess.run(
                ["git", "-C", str(repo_path), "worktree", "remove", "--force", str(worktree_path)],
                check=False,
            )
    finally:
        temp_ctx.cleanup()


def resolve_output_paths(repo_root: Path, profile_name: str, variant_names: List[str], output_arg: str | None) -> Tuple[Path, Dict[str, Path]]:
    if len(variant_names) == 1:
        only_variant = variant_names[0]
        output = Path(output_arg) if output_arg else (repo_root / "results" / "oss_validation" / "{}.json".format(profile_name))
        return output, {only_variant: output}

    if output_arg:
        summary_path = Path(output_arg)
        variant_paths = {
            name: summary_path.with_name("{}.{}.json".format(summary_path.stem, name))
            for name in variant_names
        }
    else:
        summary_path = repo_root / "results" / "oss_validation" / "{}.matrix.json".format(profile_name)
        variant_paths = {
            name: repo_root / "results" / "oss_validation" / "{}.{}.json".format(profile_name, name)
            for name in variant_names
        }
    return summary_path, variant_paths


def load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError("campaign output not found: {}".format(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("campaign output must be a JSON object: {}".format(path))
    return data


def resolve_scenario_summary(report: Dict[str, Any], scenario_name: str) -> Dict[str, Any]:
    summary = report.get("summary")
    if not isinstance(summary, dict) or not summary:
        raise ValueError("report missing summary data")

    if scenario_name in summary and isinstance(summary[scenario_name], dict):
        return summary[scenario_name]

    if len(summary) == 1:
        only = next(iter(summary.values()))
        if isinstance(only, dict):
            return only

    raise ValueError(
        "scenario '{}' missing from report summary keys: {}".format(
            scenario_name,
            ", ".join(sorted(summary.keys())),
        )
    )


def resolve_scenario_results(report: Dict[str, Any], scenario_name: str) -> List[Dict[str, Any]]:
    results = report.get("results")
    if not isinstance(results, dict) or not results:
        raise ValueError("report missing results data")

    entries = results.get(scenario_name)
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]

    if len(results) == 1:
        only = next(iter(results.values()))
        if isinstance(only, list):
            return [entry for entry in only if isinstance(entry, dict)]

    raise ValueError(
        "scenario '{}' missing from report result keys: {}".format(
            scenario_name,
            ", ".join(sorted(results.keys())),
        )
    )


def check_expectations(expect: Dict[str, Any], report: Dict[str, Any], scenario_name: str) -> List[str]:
    if not expect:
        return []

    summary = resolve_scenario_summary(report, scenario_name)
    entries = resolve_scenario_results(report, scenario_name)
    failures: List[str] = []

    bricks = int(summary.get("bricks", 0))
    brick_rate = float(summary.get("brick_rate", 0.0))

    bricks_min = expect.get("bricks_min")
    if bricks_min is not None and bricks < int(bricks_min):
        failures.append("bricks={} is below expected minimum {}".format(bricks, int(bricks_min)))

    bricks_max = expect.get("bricks_max")
    if bricks_max is not None and bricks > int(bricks_max):
        failures.append("bricks={} exceeds expected maximum {}".format(bricks, int(bricks_max)))

    brick_rate_min = expect.get("brick_rate_min")
    if brick_rate_min is not None and brick_rate < float(brick_rate_min):
        failures.append(
            "brick_rate={:.6f} is below expected minimum {:.6f}".format(brick_rate, float(brick_rate_min))
        )

    brick_rate_max = expect.get("brick_rate_max")
    if brick_rate_max is not None and brick_rate > float(brick_rate_max):
        failures.append(
            "brick_rate={:.6f} exceeds expected maximum {:.6f}".format(brick_rate, float(brick_rate_max))
        )

    if bool(expect.get("require_control_success", False)):
        control_entries = [entry for entry in entries if bool(entry.get("is_control", False))]
        failed_controls = [entry for entry in control_entries if entry.get("boot_outcome") != "success"]
        if not control_entries:
            failures.append("no control runs found (required)")
        elif failed_controls:
            outcomes = ", ".join(
                "{}:{}".format(entry.get("fault_at"), entry.get("boot_outcome"))
                for entry in failed_controls[:5]
            )
            failures.append(
                "{} control run(s) did not boot successfully: {}".format(len(failed_controls), outcomes)
            )

    return failures


def build_campaign_command(repo_root: Path, profile: Dict[str, Any], renode_test: str, output_path: Path) -> List[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scenario_name = str(profile.get("scenario", profile["name"]))
    cmd: List[str] = [
        "python3",
        "scripts/ota_fault_campaign.py",
        "--scenario",
        scenario_name,
        "--robot-suite",
        str(profile.get("robot_suite", DEFAULT_GENERIC_SUITE)),
        "--fault-range",
        str(profile["fault_range"]),
        "--fault-step",
        str(profile["fault_step"]),
        "--total-writes",
        str(profile["total_writes"]),
        "--evaluation-mode",
        str(profile.get("evaluation_mode", "execute")),
        "--boot-mode",
        str(profile.get("boot_mode", "direct")),
        "--output",
        str(output_path),
        "--renode-test",
        renode_test,
    ]

    if profile.get("slot_a_image_file"):
        cmd.extend(["--slot-a-image-file", str(profile["slot_a_image_file"])])
    if profile.get("slot_b_image_file"):
        cmd.extend(["--slot-b-image-file", str(profile["slot_b_image_file"])])
    if profile.get("ota_header_size") is not None:
        cmd.extend(["--ota-header-size", str(profile["ota_header_size"])])

    if profile.get("include_metadata_faults", False):
        cmd.append("--include-metadata-faults")
    if profile.get("trace_execution", False):
        cmd.append("--trace-execution")
    if profile.get("no_control", False):
        cmd.append("--no-control")
    if profile.get("assert_no_bricks", False):
        cmd.append("--assert-no-bricks")
    if profile.get("assert_control_boots", False):
        cmd.append("--assert-control-boots")

    for rv in profile["robot_vars"]:
        cmd.extend(["--robot-var", rv])

    for extra in normalize_list_of_strings(profile.get("campaign_args"), "campaign_args"):
        cmd.append(extra)

    return cmd


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (repo_root / manifest_path).resolve()

    manifest = load_manifest(manifest_path)
    profile = find_profile(manifest, args.profile)
    validate_profile(profile, args.allow_disallowed_licenses)

    variants_raw = profile.get("variants")
    if variants_raw is None:
        variants: List[Dict[str, Any]] = [{"name": str(profile["name"])}]
    else:
        variants = [dict(v) for v in variants_raw]

    variant_names = [str(v["name"]) for v in variants]
    summary_path, output_by_variant = resolve_output_paths(repo_root, str(profile["name"]), variant_names, args.output)

    shared_setup = normalize_list_of_strings(profile.get("setup_commands"), "setup_commands")
    shared_source = profile.get("source_checkout")
    matrix_entries: List[Dict[str, Any]] = []
    final_rc = 0

    for variant in variants:
        variant_name = str(variant["name"])
        variant_profile = deep_merge(profile, variant.get("overrides", {}))
        variant_profile.pop("variants", None)

        if "scenario" not in variant_profile:
            variant_profile["scenario"] = (
                "{}_{}".format(profile["name"], variant_name) if len(variants) > 1 else str(profile["name"])
            )

        context: Dict[str, str] = {
            "repo_root": str(repo_root),
            "manifest_dir": str(manifest_path.parent),
            "profile_name": str(profile["name"]),
            "variant_name": variant_name,
            "variant_output": str(output_by_variant[variant_name]),
            "renode_test": args.renode_test,
        }

        source_cfg = variant.get("source_checkout", shared_source)
        temp_ctx: tempfile.TemporaryDirectory[str] | None = None
        source_worktree: Path | None = None
        rc = 2
        scenario_name = str(variant_profile.get("scenario", profile["name"]))
        expectation_failures: List[str] = []

        try:
            temp_ctx, source_worktree = prepare_source_checkout(repo_root, source_cfg, context)
            if source_worktree is not None:
                context["source_worktree"] = str(source_worktree)

            rendered_profile = render_templates(variant_profile, context)
            variant_setup = normalize_list_of_strings(variant.get("setup_commands"), "variants.setup_commands")
            run_shell_commands(shared_setup + variant_setup, repo_root, context)

            command = build_campaign_command(
                repo_root=repo_root,
                profile=rendered_profile,
                renode_test=args.renode_test,
                output_path=output_by_variant[variant_name],
            )
            print(">> {}".format(" ".join(shlex.quote(part) for part in command)))
            result = subprocess.run(command, cwd=str(repo_root), check=False)
            rc = int(result.returncode)

            scenario_name = str(rendered_profile.get("scenario", profile["name"]))
            expect = rendered_profile.get("expect")
            if rc == 0 and isinstance(expect, dict) and expect:
                report = load_report(output_by_variant[variant_name])
                expectation_failures = check_expectations(expect, report, scenario_name)
                if expectation_failures:
                    rc = 1
                    print(
                        "Variant '{}' expectation check failed for scenario '{}':".format(variant_name, scenario_name),
                        file=sys.stderr,
                    )
                    for failure in expectation_failures:
                        print("  - {}".format(failure), file=sys.stderr)
        except Exception as exc:
            print("Variant '{}' failed before campaign execution: {}".format(variant_name, exc), file=sys.stderr)
            rc = 2
        finally:
            cleanup_source_checkout(source_cfg, temp_ctx, source_worktree, repo_root, context)

        final_rc = max(final_rc, rc)
        matrix_entries.append(
            {
                "variant": variant_name,
                "scenario": scenario_name,
                "output": str(output_by_variant[variant_name]),
                "return_code": rc,
                "source_worktree_used": source_worktree is not None,
                "expectation_failures": expectation_failures,
            }
        )

    if len(variants) > 1:
        summary_payload = {
            "profile": profile["name"],
            "manifest": str(manifest_path),
            "renode_test": args.renode_test,
            "variants": matrix_entries,
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
        print("matrix summary: {}".format(summary_path))

    return final_rc


if __name__ == "__main__":
    raise SystemExit(main())
