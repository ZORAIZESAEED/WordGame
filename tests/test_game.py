import pytest

from app.game import evaluate_guess, is_valid_guess, score_for_win
from app.words import ANSWERS, DATA_DIR, VALID_GUESSES, load_words


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


def test_answer_list_is_big_enough_and_has_no_duplicates():
    assert len(ANSWERS) >= 500
    assert len(set(ANSWERS)) == len(ANSWERS)


def test_answers_file_has_no_typos_hiding_in_the_raw_lines():
    # load_words strips whitespace, so check the file itself for stray characters.
    for line in (DATA_DIR / "answers.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            assert len(line) == 5 and line.isascii() and line.isalpha() and line.islower(), line


def test_guess_list_is_much_bigger_than_the_answer_list():
    assert len(VALID_GUESSES) >= 4000
    assert set(ANSWERS) <= VALID_GUESSES
    assert all(len(w) == 5 and w.isascii() and w.isalpha() and w.islower() for w in VALID_GUESSES)


@pytest.mark.parametrize("word", ["honor", "armor", "color", "fjord", "nymph"])
def test_british_and_american_spellings_are_accepted(word):
    assert is_valid_guess(word)


def test_load_words_skips_comments_and_blank_lines(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("# a comment\n\ncrane\n  slate  \n")
    assert load_words(f) == ["crane", "slate"]
