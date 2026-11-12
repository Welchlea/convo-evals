"""The checks. Each one takes a reply and returns a pass, fail or skip."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .readability import longest_sentence, reading_grade, split_words

PASS, FAIL, SKIP = "pass", "fail", "skip"

# Phrases that tell the user how to reach a person.
DEFAULT_HANDOVER_PHRASES = [
    "speak to",
    "talk to",
    "call us",
    "phone us",
    "one of our team",
    "an adviser",
    "a person",
]

# Phrases that read as personal financial advice. A regulated service
# can explain options. It must not tell someone which one to choose.
DEFAULT_ADVICE_PATTERNS = [
    r"\byou should\b",
    r"\bi(?: would|'d)? recommend\b",
    r"\bmy advice\b",
    r"\bthe best (?:option|choice|fund) for you\b",
    r"\byou(?:'d| would) be better off\b",
]


@dataclass
class CheckResult:
    check: str
    status: str
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status == FAIL


Judge = Callable[[str], str]


def _phrases(spec: dict) -> list[str]:
    phrases = spec.get("phrases") or []
    if isinstance(phrases, str):
        phrases = [phrases]
    return [str(p) for p in phrases]


def _found(reply: str, phrases: list[str]) -> list[str]:
    low = reply.lower()
    return [p for p in phrases if p.lower() in low]


def includes_all(reply: str, spec: dict, **_) -> CheckResult:
    phrases = _phrases(spec)
    missing = [p for p in phrases if p not in _found(reply, phrases)]
    if missing:
        return CheckResult("includes_all", FAIL, f"missing: {', '.join(missing)}")
    return CheckResult("includes_all", PASS)


def includes_any(reply: str, spec: dict, **_) -> CheckResult:
    phrases = _phrases(spec)
    if _found(reply, phrases):
        return CheckResult("includes_any", PASS)
    return CheckResult("includes_any", FAIL, f"none of: {', '.join(phrases)}")


def excludes(reply: str, spec: dict, **_) -> CheckResult:
    found = _found(reply, _phrases(spec))
    if found:
        return CheckResult("excludes", FAIL, f"found: {', '.join(found)}")
    return CheckResult("excludes", PASS)


def matches(reply: str, spec: dict, **_) -> CheckResult:
    pattern = spec["pattern"]
    if re.search(pattern, reply, flags=re.IGNORECASE):
        return CheckResult("matches", PASS)
    return CheckResult("matches", FAIL, f"no match for pattern: {pattern}")


def reading_grade_check(reply: str, spec: dict, **_) -> CheckResult:
    limit = float(spec.get("max", 9))
    grade = reading_grade(reply)
    if grade > limit:
        return CheckResult("reading_grade", FAIL, f"grade {grade}, limit {limit:g}")
    return CheckResult("reading_grade", PASS, f"grade {grade}")


def max_sentence_words(reply: str, spec: dict, **_) -> CheckResult:
    limit = int(spec.get("max", 25))
    count, sentence = longest_sentence(reply)
    if count > limit:
        start = " ".join(sentence.split()[:8])
        return CheckResult(
            "max_sentence_words", FAIL, f'{count} words, limit {limit}: "{start}..."'
        )
    return CheckResult("max_sentence_words", PASS)


def max_words(reply: str, spec: dict, **_) -> CheckResult:
    limit = int(spec.get("max", 80))
    count = len(split_words(reply))
    if count > limit:
        return CheckResult("max_words", FAIL, f"{count} words, limit {limit}")
    return CheckResult("max_words", PASS)


def max_questions(reply: str, spec: dict, **_) -> CheckResult:
    limit = int(spec.get("max", 1))
    count = reply.count("?")
    if count > limit:
        return CheckResult("max_questions", FAIL, f"{count} questions, limit {limit}")
    return CheckResult("max_questions", PASS)


def offers_handover(reply: str, spec: dict, **_) -> CheckResult:
    phrases = _phrases(spec) or DEFAULT_HANDOVER_PHRASES
    if _found(reply, phrases):
        return CheckResult("offers_handover", PASS)
    return CheckResult("offers_handover", FAIL, "no route to a person offered")


def no_advice(reply: str, spec: dict, **_) -> CheckResult:
    patterns = spec.get("patterns") or DEFAULT_ADVICE_PATTERNS
    for pattern in patterns:
        hit = re.search(pattern, reply, flags=re.IGNORECASE)
        if hit:
            return CheckResult("no_advice", FAIL, f'reads as advice: "{hit.group(0)}"')
    return CheckResult("no_advice", PASS)


def build_judge_prompt(user: str, reply: str, rubric: str) -> str:
    """The prompt sent to a judge model for checks that rules cannot cover."""
    return (
        "You are reviewing one reply from a customer service chatbot.\n"
        "Decide if the reply meets the rubric. Judge only against the rubric.\n\n"
        f"Rubric: {rubric.strip()}\n\n"
        f"User message: {user.strip()}\n\n"
        f"Chatbot reply: {reply.strip()}\n\n"
        "Answer on one line. Start with PASS or FAIL, then a short reason."
    )


def judge(reply: str, spec: dict, *, user: str = "", judge_fn: Judge | None = None, **_) -> CheckResult:
    """Ask a model to grade the reply. Skipped when no judge is connected."""
    if judge_fn is None:
        return CheckResult("judge", SKIP, "no judge connected")
    verdict = judge_fn(build_judge_prompt(user, reply, spec["rubric"])).strip()
    status = PASS if verdict.upper().startswith("PASS") else FAIL
    return CheckResult("judge", status, verdict)


CHECKS: dict[str, Callable[..., CheckResult]] = {
    "includes_all": includes_all,
    "includes_any": includes_any,
    "excludes": excludes,
    "matches": matches,
    "reading_grade": reading_grade_check,
    "max_sentence_words": max_sentence_words,
    "max_words": max_words,
    "max_questions": max_questions,
    "offers_handover": offers_handover,
    "no_advice": no_advice,
    "judge": judge,
}


def run_check(reply: str, spec: dict, *, user: str = "", judge_fn: Judge | None = None) -> CheckResult:
    kind = spec.get("type")
    if kind not in CHECKS:
        known = ", ".join(sorted(CHECKS))
        raise ValueError(f"Unknown check type '{kind}'. Known types: {known}")
    return CHECKS[kind](reply, spec, user=user, judge_fn=judge_fn)
