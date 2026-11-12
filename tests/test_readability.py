from convo_evals.readability import (
    count_syllables,
    longest_sentence,
    reading_grade,
    split_sentences,
)


def test_split_sentences_handles_line_breaks():
    assert split_sentences("One. Two!\nThree?") == ["One.", "Two!", "Three?"]


def test_count_syllables():
    assert count_syllables("cat") == 1
    assert count_syllables("pension") == 2
    assert count_syllables("table") == 2
    assert count_syllables("income") == 2


def test_plain_text_scores_lower_than_dense_text():
    plain = "You can sign in to see your pension. It is on the first page."
    dense = (
        "Accrued benefits are detailed within the annual valuation documentation "
        "issued subsequent to the conclusion of each scheme year."
    )
    assert reading_grade(plain) < 6
    assert reading_grade(dense) > 12


def test_empty_text_scores_zero():
    assert reading_grade("") == 0.0


def test_longest_sentence():
    count, sentence = longest_sentence("Short one. This one is a bit longer than that.")
    assert count == 8
    assert sentence.startswith("This one")
