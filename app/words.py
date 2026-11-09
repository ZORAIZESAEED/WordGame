"""Word lists for the game, loaded once at import from app/data/.

- answers.txt: the words a game can pick. Hand-picked, common and family-friendly,
  British spelling.
- allowed.txt: every word accepted as a guess. Five-letter words from SCOWL's British
  and American lists (see data/SCOWL-LICENSE.txt), so "armor" and "colour"-style
  spellings both work.
"""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


def load_words(path: Path) -> list[str]:
    """One word per line. Blank lines and lines starting with # are skipped."""
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            words.append(word)
    return words


ANSWERS: list[str] = load_words(DATA_DIR / "answers.txt")

# Answers are always valid guesses, even if someone edits one list and not the other.
VALID_GUESSES: frozenset[str] = frozenset(load_words(DATA_DIR / "allowed.txt")) | frozenset(ANSWERS)
