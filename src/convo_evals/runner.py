"""Load a suite of test cases and run every check against the replies."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .graders import FAIL, SKIP, CheckResult, Judge, run_check


@dataclass
class CaseResult:
    case_id: str
    user: str
    reply: str
    tags: list[str]
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(c.failed for c in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.failed]


@dataclass
class SuiteResult:
    name: str
    cases: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def skipped_checks(self) -> int:
        return sum(1 for c in self.cases for k in c.checks if k.status == SKIP)

    def failures_by_check(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in self.cases:
            for check in case.failures:
                counts[check.check] = counts.get(check.check, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return data


def load_replies(path: str | Path) -> dict[str, str]:
    data = load_yaml(path)
    replies = data.get("replies", data)
    return {str(k): str(v).strip() for k, v in replies.items()}


def run_suite(suite: dict, replies: dict[str, str], judge_fn: Judge | None = None) -> SuiteResult:
    default_checks = (suite.get("defaults") or {}).get("checks") or []
    results = []
    seen: set[str] = set()
    for case in suite.get("cases") or []:
        case_id = str(case["id"])
        if case_id in seen:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        user = str(case.get("user", ""))
        result = CaseResult(case_id, user, replies.get(case_id, ""), list(case.get("tags") or []))
        if case_id not in replies:
            result.checks.append(CheckResult("reply_recorded", FAIL, "no reply recorded for this case"))
        else:
            for spec in [*default_checks, *(case.get("checks") or [])]:
                result.checks.append(run_check(result.reply, spec, user=user, judge_fn=judge_fn))
        results.append(result)
    return SuiteResult(str(suite.get("suite", "Unnamed suite")), results)


def compare(before: SuiteResult, after: SuiteResult) -> dict[str, list[str]]:
    """Sort cases into fixed, regressed, still failing and still passing."""
    old = {c.case_id: c.passed for c in before.cases}
    groups: dict[str, list[str]] = {"fixed": [], "regressed": [], "still_failing": [], "still_passing": []}
    for case in after.cases:
        was = old.get(case.case_id)
        if was is None:
            continue
        if case.passed and not was:
            groups["fixed"].append(case.case_id)
        elif not case.passed and was:
            groups["regressed"].append(case.case_id)
        elif case.passed:
            groups["still_passing"].append(case.case_id)
        else:
            groups["still_failing"].append(case.case_id)
    return groups
