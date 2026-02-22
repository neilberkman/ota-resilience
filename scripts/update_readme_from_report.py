#!/usr/bin/env python3
"""Render README comparative-table section from a live campaign report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


START_MARKER = "<!-- COMPARATIVE_TABLE:START -->"
END_MARKER = "<!-- COMPARATIVE_TABLE:END -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update README comparative table from campaign report JSON")
    parser.add_argument("--report", default="results/campaign_report.json")
    parser.add_argument("--readme", default="README.md")
    return parser.parse_args()


def get_required(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError("missing required string field: {}".format(field))
    return value


def render_section(report_path: Path, payload: dict) -> str:
    engine = get_required(payload, "engine")
    if engine != "renode-test":
        raise ValueError("refusing README update from non-live report engine={!r}".format(engine))

    comparative_table = get_required(payload, "comparative_table")
    execution = payload.get("execution", {})
    git_data = payload.get("git", {})

    run_utc = str(execution.get("run_utc", "unknown"))
    command = str(execution.get("campaign_command", "unknown"))
    commit_raw = str(git_data.get("short_commit") or git_data.get("commit") or "")
    if not commit_raw or commit_raw == "unknown":
        commit = "unavailable (no commits yet)"
    else:
        commit = commit_raw
    dirty = str(git_data.get("dirty", "unknown"))

    lines = [
        START_MARKER,
        "```text",
        comparative_table,
        "```",
        "",
        "Generated from live campaign report metadata:",
        "- Engine: `{}`".format(engine),
        "- Run UTC: `{}`".format(run_utc),
        "- Command: `{}`".format(command),
        "- Git commit: `{}`".format(commit),
        "- Git dirty: `{}`".format(dirty),
        "- Source report: `{}`".format(report_path.as_posix()),
        END_MARKER,
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    report_path = Path(args.report)
    readme_path = Path(args.readme)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    section = render_section(report_path, payload)

    readme = readme_path.read_text(encoding="utf-8")
    if START_MARKER not in readme or END_MARKER not in readme:
        raise ValueError("README markers not found: {} .. {}".format(START_MARKER, END_MARKER))

    pre, _sep, rest = readme.partition(START_MARKER)
    _body, _sep2, post = rest.partition(END_MARKER)
    updated = pre + section + post
    readme_path.write_text(updated, encoding="utf-8")

    print("updated {} from {}".format(readme_path.as_posix(), report_path.as_posix()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
