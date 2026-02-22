#!/usr/bin/env python3
"""Shared fault-campaign data structures and helpers."""

from __future__ import annotations

import dataclasses
from typing import Any, Iterable, Optional


@dataclasses.dataclass
class FaultResult:
    fault_at: int
    boot_outcome: str
    boot_slot: Optional[str]
    nvm_state: Any
    raw_log: str
    fault_diagnostics: Any = dataclasses.field(default_factory=dict)
    is_control: bool = False


def parse_fault_range(expr: str) -> Iterable[int]:
    start_s, end_s = expr.split(":", 1)
    start = int(start_s)
    end = int(end_s)
    if end < start:
        raise ValueError("invalid fault range: {}".format(expr))
    return range(start, end + 1)
