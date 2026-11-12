import pytest

from convo_evals.graders import FAIL, PASS, SKIP, build_judge_prompt, run_check


def status(reply, spec, **kwargs):
    return run_check(reply, spec, **kwargs).status


def test_includes_all_is_case_insensitive():
    assert status("Please Sign In first", {"type": "includes_all", "phrases": ["sign in"]}) == PASS
    assert status("Hello", {"type": "includes_all", "phrases": ["sign in"]}) == FAIL


def test_includes_any():
    spec = {"type": "includes_any", "phrases": ["sign in", "log in"]}
    assert status("Log in to see it", spec) == PASS
    assert status("Look online", spec) == FAIL


def test_excludes_reports_what_it_found():
    result = run_check("You must crystallise it", {"type": "excludes", "phrases": ["crystallise"]})
    assert result.status == FAIL
    assert "crystallise" in result.detail


def test_matches_pattern():
    assert status("Which one do you need?", {"type": "matches", "pattern": r"\?$"}) == PASS
    assert status("Tell me more.", {"type": "matches", "pattern": r"\?$"}) == FAIL


def test_max_questions():
    assert status("One? Two?", {"type": "max_questions", "max": 1}) == FAIL
    assert status("One?", {"type": "max_questions", "max": 1}) == PASS


def test_max_sentence_words():
    long = "This sentence keeps going and going with far too many words in it to be clear."
    assert status(long, {"type": "max_sentence_words", "max": 10}) == FAIL
    assert status("Short and clear.", {"type": "max_sentence_words", "max": 10}) == PASS


def test_offers_handover_uses_default_phrases():
    assert status("You can speak to one of our team.", {"type": "offers_handover"}) == PASS
    assert status("Fill in form BW12.", {"type": "offers_handover"}) == FAIL


@pytest.mark.parametrize(
    "reply",
    [
        "You should move your pension.",
        "I recommend the growth fund.",
        "I'd recommend waiting.",
        "The best option for you is fund B.",
    ],
)
def test_no_advice_catches_advice(reply):
    assert status(reply, {"type": "no_advice"}) == FAIL


def test_no_advice_allows_explaining_options():
    reply = "I cannot tell you which fund to choose. A higher risk fund can grow more."
    assert status(reply, {"type": "no_advice"}) == PASS


def test_judge_is_skipped_without_a_judge():
    assert status("Anything", {"type": "judge", "rubric": "Is kind"}) == SKIP


def test_judge_uses_the_function_it_is_given():
    spec = {"type": "judge", "rubric": "Is kind"}
    assert status("Hi", spec, judge_fn=lambda prompt: "PASS: kind") == PASS
    assert status("Hi", spec, judge_fn=lambda prompt: "FAIL: cold") == FAIL


def test_judge_prompt_contains_all_three_parts():
    prompt = build_judge_prompt("my question", "the reply", "the rubric")
    assert "my question" in prompt and "the reply" in prompt and "the rubric" in prompt


def test_unknown_check_type_is_an_error():
    with pytest.raises(ValueError, match="Unknown check type"):
        run_check("Hi", {"type": "nope"})
