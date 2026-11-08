"""Pure game logic. No web or database code in here, so it is easy to test."""

import random
from typing import Literal

from .words import ANSWERS, VALID_GUESSES

MAX_ATTEMPTS = 6
WORD_LENGTH = 5

Mark = Literal["correct", "present", "absent"]


def pick_word(rng: random.Random | None = None) -> str:
    return (rng or random).choice(ANSWERS)


def is_valid_guess(word: str) -> bool:
    return len(word) == WORD_LENGTH and word in VALID_GUESSES


def evaluate_guess(secret: str, guess: str) -> list[Mark]:
    """Mark each letter of the guess.

    Handles repeated letters properly: a letter is only marked "present"
    as many times as it still appears unmatched in the secret.
    """
    if len(secret) != len(guess):
        raise ValueError("secret and guess must be the same length")

    result: list[Mark] = ["absent"] * len(guess)
    remaining: dict[str, int] = {}

    # First pass: exact matches, and count the secret letters left over.
    for i, (s, g) in enumerate(zip(secret, guess, strict=True)):
        if s == g:
            result[i] = "correct"
        else:
            remaining[s] = remaining.get(s, 0) + 1

    # Second pass: right letter, wrong place.
    for i, g in enumerate(guess):
        if result[i] == "correct":
            continue
        if remaining.get(g, 0) > 0:
            result[i] = "present"
            remaining[g] -= 1

    return result


def score_for_win(attempts_used: int) -> int:
    """100 points per unused attempt, plus 100 for winning at all."""
    return (MAX_ATTEMPTS - attempts_used + 1) * 100
