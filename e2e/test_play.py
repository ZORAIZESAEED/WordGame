"""Play the real game in a browser, mostly on a phone-sized screen.

Playwright only treats a pattern as a regex when it's an re.compile() object; a plain
string is matched literally.
"""

import itertools
import re

from playwright.sync_api import Page, expect

from app import daily

_names = itertools.count(1)


def new_player() -> str:
    # The server's database lasts the whole session and the daily is one game per name
    # per day, so every test plays as somebody new.
    return f"tester{next(_names)}"


def todays_word() -> str:
    return daily.word_for(daily.today())  # DAILY_WORD_SECRET is set in conftest.py


def tap_word(page: Page, word: str) -> None:
    for ch in word:
        page.locator(f'.key[data-key="{ch}"]').tap()
    page.locator('.key[data-key="Enter"]').tap()


def start(page: Page, mode: str = "daily", name: str | None = None) -> str:
    name = name or new_player()
    page.goto("/")
    page.fill("#player", name)
    page.locator("#daily-btn" if mode == "daily" else "button.secondary").first.click()
    expect(page.locator("#keyboard")).to_be_visible()
    return name


def row(page: Page, n: int):
    return page.locator(".board .row").nth(n)


def test_daily_game_on_a_phone(phone):
    # Make Share fall back to the clipboard so the test can read what was shared.
    phone.add_init_script("Object.defineProperty(navigator, 'share', { value: undefined })")
    name = start(phone)
    expect(phone.locator("#mode-label")).to_have_text(
        f"Daily #{daily.puzzle_number(daily.today())} · {name}"
    )

    tap_word(phone, "abo")  # three letters, then Enter
    expect(phone.locator("#toasts")).to_contain_text("Not enough letters")
    expect(row(phone, 0)).to_have_class("row shake")

    for _ in range(3):
        phone.locator('.key[data-key="Backspace"]').tap()
    tap_word(phone, "zzzzz")
    expect(phone.locator("#toasts")).to_contain_text("Not in the word list")

    for _ in range(5):
        phone.locator('.key[data-key="Backspace"]').tap()
    first = "about" if todays_word() != "about" else "crane"
    tap_word(phone, first)
    expect(row(phone, 0)).to_have_attribute(
        "aria-label",
        f"{first.upper()}: "
        + ", ".join(
            f"{ch.upper()} {m}" for ch, m in zip(first, _marks(todays_word(), first), strict=True)
        ),
    )
    # Every letter of the guess now has a colour on the keyboard.
    for ch in set(first):
        expect(phone.locator(f'.key[data-key="{ch}"]')).to_have_class(
            f"key {_best_mark(todays_word(), first, ch)}"
        )

    tap_word(phone, todays_word())
    stats = phone.locator("#stats-dialog")
    expect(stats).to_be_visible(timeout=10_000)
    expect(phone.locator("#st-played")).to_have_text("1")
    expect(phone.locator("#st-streak")).to_have_text("1")
    expect(phone.locator("#distribution .bar.highlight")).to_have_text("1")
    expect(phone.locator("#countdown")).to_have_text(re.compile(r"\d\d:\d\d:\d\d"))

    phone.locator("#share-btn").tap()
    expect(phone.locator("#toasts")).to_contain_text("Copied")
    shared = phone.evaluate("navigator.clipboard.readText()")
    lines = shared.splitlines()
    assert lines[0] == f"Word Game Daily #{daily.puzzle_number(daily.today())} 2/6"
    assert lines[2:] and all(set(line) <= set("🟩🟨⬛") for line in lines[2:])
    assert lines[-1] == "🟩" * 5
    assert todays_word() not in shared.lower()  # sharing never gives the word away

    assert phone.errors == []


def test_typing_on_a_real_keyboard(page_for):
    page = page_for("Desktop Chrome")
    start(page, mode="practice")
    page.keyboard.type("abxx")
    page.keyboard.press("Backspace")
    page.keyboard.press("Backspace")
    page.keyboard.type("out")
    page.keyboard.press("Enter")
    expect(row(page, 0)).to_have_attribute("aria-label", re.compile(r"ABOUT: .*"))
    assert page.errors == []


def test_daily_picks_up_where_you_left_off(phone):
    name = start(phone)
    first = "about" if todays_word() != "about" else "crane"
    tap_word(phone, first)
    expect(row(phone, 0)).to_have_attribute("aria-label", re.compile(rf"{first.upper()}: .*"))

    phone.reload()
    start(phone, name=name)
    expect(row(phone, 0)).to_have_attribute("aria-label", re.compile(rf"{first.upper()}: .*"))
    expect(row(phone, 1)).to_have_attribute("aria-label", "Row 2")


def test_practice_from_the_results_screen(phone):
    name = start(phone)
    tap_word(phone, todays_word())
    expect(phone.locator("#stats-dialog")).to_be_visible(timeout=10_000)
    phone.locator("#again-btn").tap()
    expect(phone.locator("#mode-label")).to_have_text(f"Practice · {name}")
    expect(phone.locator("#stats-dialog")).to_be_hidden()
    expect(row(phone, 0)).to_have_attribute("aria-label", "Row 1")


def test_leaderboard_shows_names_as_text(phone):
    start(phone, name="<b>bold</b>")
    tap_word(phone, todays_word())
    expect(phone.locator("#stats-dialog")).to_be_visible(timeout=10_000)
    phone.locator("#stats-dialog .close").tap()

    phone.locator("#boards-btn").tap()
    board = phone.locator("#daily-leaders")
    expect(board).to_contain_text("<b>bold</b>")
    assert board.locator("b").count() == 0


def test_fits_a_small_phone_without_scrolling(page_for):
    page = page_for("iPhone SE")
    start(page, mode="practice")
    fits = page.evaluate(
        """() => {
          const kb = document.getElementById('keyboard').getBoundingClientRect();
          const board = document.getElementById('board').getBoundingClientRect();
          return {
            noSideScroll: document.documentElement.scrollWidth <= innerWidth,
            keyboardOnScreen: kb.bottom <= innerHeight + 1,
            boardAboveKeyboard: board.bottom <= kb.top,
          };
        }"""
    )
    assert fits == {"noSideScroll": True, "keyboardOnScreen": True, "boardAboveKeyboard": True}


def test_first_visit_shows_the_rules_once(browser, server):
    ctx = browser.new_context(base_url=server)
    page = ctx.new_page()
    page.goto("/")
    expect(page.locator("#help-dialog")).to_be_visible()
    page.locator("#help-dialog .close").click()
    page.reload()
    expect(page.locator("#help-dialog")).to_be_hidden()
    ctx.close()


# --- helpers that mirror the game rules, so the expected colours aren't hard-coded ---


def _marks(secret: str, guess: str) -> list[str]:
    from app.game import evaluate_guess

    return evaluate_guess(secret, guess)


def _best_mark(secret: str, guess: str, ch: str) -> str:
    rank = {"absent": 1, "present": 2, "correct": 3}
    marks = [m for g, m in zip(guess, _marks(secret, guess), strict=True) if g == ch]
    return max(marks, key=rank.__getitem__)
