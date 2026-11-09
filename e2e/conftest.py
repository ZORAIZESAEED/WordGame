"""Browser tests: start the real app on a spare port and drive it with Chromium.

Run with:  pytest e2e
Needs:     pip install -r requirements-e2e.txt && python -m playwright install chromium

Set CHROMIUM_PATH to use a Chromium that's already installed instead of Playwright's own.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parent.parent

# Shared by the server (it inherits the environment) and the tests, so both agree on the
# daily word: tests call daily.word_for(), which reads the same variable.
os.environ["DAILY_WORD_SECRET"] = "e2e-tests"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def server(tmp_path_factory) -> Iterator[str]:
    port = _free_port()
    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db}",
        "NO_PROXY": "*",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(100):
        try:
            opener.open(url + "/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("the app didn't start")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def pw() -> Iterator[Playwright]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(pw) -> Iterator[Browser]:
    b = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None)
    yield b
    b.close()


@pytest.fixture()
def page_for(browser, server, pw):
    """Make a fresh page for a device ("iPhone 13", "Desktop Chrome", ...), with the
    first-visit rules already dismissed and page errors collected in page.errors."""
    contexts = []

    def _make(device: str = "iPhone 13", **extra) -> Page:
        ctx = browser.new_context(
            **pw.devices[device],
            base_url=server,
            permissions=["clipboard-read", "clipboard-write"],
            **extra,
        )
        ctx.add_init_script("localStorage.setItem('seen-help', '1')")
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []  # type: ignore[attr-defined]
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        return page

    yield _make
    for ctx in contexts:
        ctx.close()


@pytest.fixture()
def phone(page_for) -> Page:
    return page_for("iPhone 13")
