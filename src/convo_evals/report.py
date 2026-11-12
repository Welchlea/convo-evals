"""Turn results into text for the terminal, Markdown or JSON."""

from __future__ import annotations

import json

from .runner import SuiteResult


def to_text(result: SuiteResult) -> str:
    lines = [f"Suite: {result.name}", ""]
    for case in result.cases:
        mark = "PASS" if case.passed else "FAIL"
        lines.append(f"{mark}  {case.case_id}")
        for check in case.failures:
            lines.append(f"      {check.check}: {check.detail}")
    lines.append("")
    lines.append(f"{result.passed} of {result.total} cases passed ({result.pass_rate:.0%})")
    by_check = result.failures_by_check()
    if by_check:
        lines.append("Failures by check: " + ", ".join(f"{k} {v}" for k, v in by_check.items()))
    if result.skipped_checks:
        noun = "check" if result.skipped_checks == 1 else "checks"
        lines.append(f"{result.skipped_checks} judge {noun} skipped (no judge connected)")
    return "\n".join(lines)


def to_markdown(result: SuiteResult) -> str:
    lines = [
        f"# Eval report: {result.name}",
        "",
        f"**{result.passed} of {result.total} cases passed ({result.pass_rate:.0%})**",
        "",
        "| Case | Result | What failed |",
        "| --- | --- | --- |",
    ]
    for case in result.cases:
        mark = "Pass" if case.passed else "Fail"
        why = "; ".join(f"{c.check}: {c.detail}" for c in case.failures).replace("|", "/")
        lines.append(f"| {case.case_id} | {mark} | {why} |")
    by_check = result.failures_by_check()
    if by_check:
        lines += ["", "## Failures by check", "", "| Check | Failures |", "| --- | --- |"]
        lines += [f"| {name} | {count} |" for name, count in by_check.items()]
    return "\n".join(lines) + "\n"


def to_json(result: SuiteResult) -> str:
    payload = {
        "suite": result.name,
        "total": result.total,
        "passed": result.passed,
        "pass_rate": round(result.pass_rate, 4),
        "cases": [
            {
                "id": case.case_id,
                "passed": case.passed,
                "tags": case.tags,
                "checks": [
                    {"check": c.check, "status": c.status, "detail": c.detail} for c in case.checks
                ],
            }
            for case in result.cases
        ],
    }
    return json.dumps(payload, indent=2)


def comparison_text(groups: dict[str, list[str]]) -> str:
    labels = [
        ("fixed", "Fixed"),
        ("regressed", "Regressed"),
        ("still_failing", "Still failing"),
        ("still_passing", "Still passing"),
    ]
    lines = []
    for key, label in labels:
        ids = groups[key]
        lines.append(f"{label} ({len(ids)}): {', '.join(ids) if ids else 'none'}")
    return "\n".join(lines)
