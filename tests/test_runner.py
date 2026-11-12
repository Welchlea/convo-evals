from pathlib import Path

import pytest

from convo_evals import report
from convo_evals.cli import main
from convo_evals.runner import compare, load_replies, load_yaml, run_suite

EXAMPLES = Path(__file__).parent.parent / "examples"

SUITE = {
    "suite": "Tiny",
    "defaults": {"checks": [{"type": "max_questions", "max": 1}]},
    "cases": [
        {"id": "a", "user": "Hi", "checks": [{"type": "includes_all", "phrases": ["hello"]}]},
        {"id": "b", "user": "Bye"},
    ],
}


def test_default_checks_apply_to_every_case():
    result = run_suite(SUITE, {"a": "Hello", "b": "What? Why?"})
    assert [c.passed for c in result.cases] == [True, False]
    assert result.failures_by_check() == {"max_questions": 1}


def test_missing_reply_fails_the_case():
    result = run_suite(SUITE, {"a": "Hello"})
    assert result.cases[1].failures[0].check == "reply_recorded"


def test_duplicate_ids_are_an_error():
    suite = {"cases": [{"id": "a"}, {"id": "a"}]}
    with pytest.raises(ValueError, match="Duplicate"):
        run_suite(suite, {"a": "x"})


def test_compare_sorts_cases_into_groups():
    before = run_suite(SUITE, {"a": "Nope", "b": "Fine."})
    after = run_suite(SUITE, {"a": "Hello", "b": "What? Why?"})
    groups = compare(before, after)
    assert groups["fixed"] == ["a"]
    assert groups["regressed"] == ["b"]


def test_example_suite_first_draft_fails_and_rewrite_passes():
    suite = load_yaml(EXAMPLES / "cases.yaml")
    v1 = run_suite(suite, load_replies(EXAMPLES / "replies_v1.yaml"))
    v2 = run_suite(suite, load_replies(EXAMPLES / "replies_v2.yaml"))
    assert v1.passed == 2
    assert v2.passed == v2.total == 8


def test_reports_render():
    result = run_suite(SUITE, {"a": "Hello", "b": "What? Why?"})
    assert "1 of 2 cases passed" in report.to_text(result)
    assert "| b | Fail |" in report.to_markdown(result)
    assert '"pass_rate": 0.5' in report.to_json(result)


def test_cli_exit_codes(capsys):
    cases = str(EXAMPLES / "cases.yaml")
    assert main(["run", cases, "--replies", str(EXAMPLES / "replies_v2.yaml")]) == 0
    assert main(["run", cases, "--replies", str(EXAMPLES / "replies_v1.yaml")]) == 1
    assert main(["run", cases, "--replies", str(EXAMPLES / "replies_v1.yaml"), "--min-pass-rate", "0.2"]) == 0
    capsys.readouterr()
