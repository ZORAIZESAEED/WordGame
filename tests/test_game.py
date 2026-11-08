import pytest

from app.game import evaluate_guess, is_valid_guess, score_for_win
from app.words import ANSWERS


def test_all_correct():
    assert evaluate_guess("crane", "crane") == ["correct"] * 5


def test_all_absent():
    assert evaluate_guess("crane", "buddy") == ["absent"] * 5


def test_present_letters():
    # a is in the word but in the wrong place, r and e are exactly right
    assert evaluate_guess("crane", "arise") == ["present", "correct", "absent", "absent", "correct"]


def test_duplicate_letters_only_marked_as_often_as_they_appear():
    # secret has one 'e'; guess has two. Only the first unmatched one counts.
    marks = evaluate_guess("crane", "geese")
    assert marks.count("correct") == 1  # final e
    assert marks.count("present") == 0


def test_exact_match_takes_priority_over_present():
    # secret "abbey": guess "babes" -> b(present) a(present) b(correct) e(correct) s(absent)
    expected = ["present", "present", "correct", "correct", "absent"]
    assert evaluate_guess("abbey", "babes") == expected


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        evaluate_guess("crane", "cranes")


def test_valid_guess():
    assert is_valid_guess("crane")
    assert not is_valid_guess("zzzzz")
    assert not is_valid_guess("cat")


def test_score():
    assert score_for_win(1) == 600
    assert score_for_win(6) == 100


def test_every_answer_is_five_letters_and_guessable():
    for w in ANSWERS:
        assert len(w) == 5 and w.isalpha() and w.islower()
        assert is_valid_guess(w)
