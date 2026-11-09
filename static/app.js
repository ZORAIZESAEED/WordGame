// Word Game frontend. No build step and no libraries: plain DOM and fetch.
"use strict";

const LEN = 5;
const MAX = 6;
const FLIP_MS = 250; // delay between tiles when a row turns over
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const WIN_WORDS = ["Genius", "Magnificent", "Impressive", "Splendid", "Great", "Phew"];
const RANK = { absent: 1, present: 2, correct: 3 };

const $ = (id) => document.getElementById(id);
const state = { player: "", game: null, input: "", busy: false, dailyNumber: null };

// --- small helpers --------------------------------------------------------------

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI sends a string for our own errors and a list for validation errors.
    const d = data.detail;
    throw new Error((Array.isArray(d) ? d.map((e) => e.msg).join(", ") : d) || "Something went wrong");
  }
  return data;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, reducedMotion ? 0 : ms));

function toast(text, ms = 1600) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  $("toasts").prepend(el);
  setTimeout(() => {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 300);
  }, ms);
}

// localStorage can be missing or blocked (private mode); the game works without it.
const store = {
  get(key) { try { return localStorage.getItem(key) || ""; } catch { return ""; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* ignore */ } },
};

// --- board ------------------------------------------------------------------------

function buildBoard() {
  const board = $("board");
  board.replaceChildren();
  for (let r = 0; r < MAX; r++) {
    const row = document.createElement("div");
    row.className = "row";
    row.setAttribute("role", "row");
    for (let c = 0; c < LEN; c++) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.setAttribute("role", "gridcell");
      row.appendChild(tile);
    }
    board.appendChild(row);
  }
}

const rowEl = (r) => $("board").children[r];

// Size the tiles to the space that's actually left between the header and the keyboard.
// CSS alone can only guess how tall those are, and fonts differ between phones, so a
// guess that fits on one device can push the board under the keyboard on another.
function fitBoard() {
  const play = $("play");
  if (play.hidden) return;
  const label = $("mode-label");
  const css = getComputedStyle(label);
  const labelH = label.offsetHeight + parseFloat(css.marginTop) + parseFloat(css.marginBottom);
  const gap = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--gap")) || 5;
  const height = play.clientHeight - labelH - 8; // a little breathing room above the keys
  const width = play.clientWidth - 32;
  const tile = Math.floor(Math.min(62, (width - gap * (LEN - 1)) / LEN, (height - gap * (MAX - 1)) / MAX));
  document.documentElement.style.setProperty("--tile", `${Math.max(tile, 24)}px`);
}

function paintRow(r, word, marks) {
  const row = rowEl(r);
  [...row.children].forEach((tile, c) => {
    tile.textContent = word[c] || "";
    tile.className = "tile" + (marks ? " " + marks[c] : word[c] ? " filled" : "");
  });
  row.setAttribute(
    "aria-label",
    marks ? `${word.toUpperCase()}: ${marks.map((m, i) => `${word[i].toUpperCase()} ${m}`).join(", ")}` : `Row ${r + 1}`
  );
}

function renderBoard() {
  const g = state.game;
  for (let r = 0; r < MAX; r++) {
    if (r < g.guesses.length) paintRow(r, g.guesses[r].word, g.guesses[r].marks);
    else if (r === g.guesses.length && g.status === "playing") paintRow(r, state.input, null);
    else paintRow(r, "", null);
  }
}

async function revealRow(r, guess) {
  const tiles = [...rowEl(r).children];
  tiles.forEach((t, c) => { t.textContent = guess.word[c]; });
  for (let c = 0; c < LEN; c++) {
    const tile = tiles[c];
    tile.classList.remove("filled");
    tile.classList.add("flip");
    // Change colour halfway through the flip, when the tile is edge-on.
    setTimeout(() => tile.classList.add(guess.marks[c]), reducedMotion ? 0 : FLIP_MS);
    await sleep(FLIP_MS);
  }
  await sleep(FLIP_MS * 2);
  tiles.forEach((t) => t.classList.remove("flip"));
  paintRow(r, guess.word, guess.marks);
}

function shakeRow(r) {
  const row = rowEl(r);
  if (!row) return;
  row.classList.remove("shake");
  void row.offsetWidth; // restart the animation if it's already run
  row.classList.add("shake");
}

// --- keyboard ---------------------------------------------------------------------

const LAYOUT = ["qwertyuiop", "asdfghjkl", "+zxcvbnm-"]; // + is Enter, - is Backspace

function buildKeyboard() {
  const kb = $("keyboard");
  kb.replaceChildren();
  LAYOUT.forEach((letters, i) => {
    const row = document.createElement("div");
    row.className = "key-row" + (i === 1 ? " middle" : "");
    for (const ch of letters) {
      const key = document.createElement("button");
      key.type = "button";
      key.className = "key";
      if (ch === "+") {
        key.textContent = "Enter";
        key.dataset.key = "Enter";
        key.classList.add("wide");
      } else if (ch === "-") {
        key.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M9 6h11v12H9l-6-6z M12 9l5 6 M17 9l-5 6" fill="none" stroke="#fff" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/></svg>';
        key.dataset.key = "Backspace";
        key.setAttribute("aria-label", "Delete letter");
        key.classList.add("wide");
      } else {
        key.textContent = ch;
        key.dataset.key = ch;
      }
      row.appendChild(key);
    }
    kb.appendChild(row);
  });
}

function paintKeys() {
  const best = {};
  for (const g of state.game.guesses) {
    [...g.word].forEach((ch, i) => {
      const m = g.marks[i];
      if (!best[ch] || RANK[m] > RANK[best[ch]]) best[ch] = m;
    });
  }
  for (const key of $("keyboard").querySelectorAll(".key")) {
    const ch = key.dataset.key;
    key.classList.remove("correct", "present", "absent");
    if (best[ch]) key.classList.add(best[ch]);
    if (ch.length === 1) key.setAttribute("aria-label", best[ch] ? `${ch} ${best[ch]}` : ch);
  }
}

function press(key) {
  const g = state.game;
  if (!g || g.status !== "playing" || state.busy || document.querySelector("dialog[open]")) return;
  const r = g.guesses.length;
  if (key === "Enter") return submitGuess();
  if (key === "Backspace") state.input = state.input.slice(0, -1);
  else if (/^[a-z]$/.test(key) && state.input.length < LEN) state.input += key;
  else return;
  paintRow(r, state.input, null);
}

// --- playing ----------------------------------------------------------------------

async function submitGuess() {
  const g = state.game;
  const r = g.guesses.length;
  if (state.input.length < LEN) {
    shakeRow(r);
    toast("Not enough letters");
    return;
  }
  state.busy = true;
  try {
    const updated = await api(`/api/games/${g.id}/guesses`, {
      method: "POST",
      body: JSON.stringify({ word: state.input }),
    });
    state.input = "";
    await revealRow(r, updated.guesses[r]);
    state.game = updated;
    paintKeys();
    if (updated.status !== "playing") await finish(updated);
  } catch (err) {
    shakeRow(r);
    toast(err.message);
  } finally {
    state.busy = false;
  }
}

async function finish(game) {
  if (game.status === "won") {
    rowEl(game.guesses.length - 1).classList.add("win");
    toast(WIN_WORDS[game.guesses.length - 1], 2000);
  } else {
    toast(game.answer.toUpperCase(), 4000);
  }
  await sleep(1600);
  openStats();
}

function showGame(game) {
  state.game = game;
  state.input = "";
  $("start").hidden = true;
  $("play").hidden = false;
  $("keyboard").hidden = false;
  $("mode-label").textContent =
    `${game.mode === "daily" ? `Daily #${game.daily_number}` : "Practice"} · ${game.player}`;
  buildBoard();
  renderBoard();
  paintKeys();
  fitBoard();
  if (game.status !== "playing") openStats();
}

async function start(mode) {
  const name = $("player").value.trim();
  state.player = name;
  store.set("player", name);
  const path = mode === "practice" ? "/api/games" : "/api/daily";
  try {
    showGame(await api(path, { method: "POST", body: JSON.stringify({ player: name }) }));
  } catch (err) {
    toast(err.message);
  }
}

// --- sharing ----------------------------------------------------------------------

const EMOJI = { correct: "🟩", present: "🟨", absent: "⬛" };

function shareText(game) {
  const score = game.status === "won" ? game.guesses.length : "X";
  const title = game.mode === "daily" ? `Word Game Daily #${game.daily_number}` : "Word Game (practice)";
  const grid = game.guesses.map((g) => g.marks.map((m) => EMOJI[m]).join("")).join("\n");
  return `${title} ${score}/${MAX}\n\n${grid}`;
}

async function share() {
  const text = shareText(state.game);
  // The phone share sheet where there is one, the clipboard everywhere else.
  if (navigator.share && matchMedia("(pointer: coarse)").matches) {
    try { await navigator.share({ text }); return; } catch (err) { if (err.name === "AbortError") return; }
  }
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard");
  } catch {
    toast("Couldn't copy. Try again?");
  }
}

// --- dialogs ----------------------------------------------------------------------

let countdownTimer = null;

function updateCountdown() {
  const now = new Date();
  const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  const s = Math.max(0, Math.floor((next - now.getTime()) / 1000));
  const pad = (n) => String(n).padStart(2, "0");
  $("countdown").textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
}

async function openStats() {
  const dlg = $("stats-dialog");
  const finished = state.game && state.game.status !== "playing";
  $("finished-actions").hidden = !finished;
  if (finished) {
    updateCountdown();
    clearInterval(countdownTimer);
    countdownTimer = setInterval(updateCountdown, 1000);
  }
  if (!dlg.open) dlg.showModal();

  if (!state.player) {
    $("stats-empty").hidden = false;
    $("stats-body").hidden = true;
    return;
  }
  try {
    const s = await api(`/api/players/${encodeURIComponent(state.player)}/stats`);
    const d = s.daily;
    $("stats-empty").hidden = d.played > 0 || s.practice.played > 0;
    $("stats-body").hidden = false;
    $("st-played").textContent = d.played;
    $("st-rate").textContent = d.win_rate;
    $("st-streak").textContent = d.current_streak;
    $("st-best").textContent = d.max_streak;
    const most = Math.max(1, ...d.distribution);
    const thisGame = state.game && state.game.mode === "daily" && state.game.status === "won"
      ? state.game.guesses.length : null;
    $("distribution").replaceChildren(...d.distribution.map((n, i) => {
      const li = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = i + 1;
      const bar = document.createElement("span");
      bar.className = "bar" + (thisGame === i + 1 ? " highlight" : "");
      bar.style.width = `${Math.max(7, (100 * n) / most)}%`;
      bar.textContent = n;
      li.append(label, bar);
      return li;
    }));
    $("practice-line").textContent = s.practice.played
      ? `Practice: ${s.practice.wins} won out of ${s.practice.played} played.`
      : "No practice games yet.";
  } catch (err) {
    toast(err.message);
  }
}

function fillLeaders(list, rows) {
  if (!rows.length) {
    const li = document.createElement("li");
    li.textContent = "No winners yet";
    list.replaceChildren(li);
    return;
  }
  list.replaceChildren(...rows.map((r) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = r.player; // textContent, so names can't inject HTML
    li.append(name, ` ${r.score}`);
    return li;
  }));
}

async function openBoards() {
  $("boards-dialog").showModal();
  try {
    const [today, allTime] = await Promise.all([api("/api/daily/leaderboard"), api("/api/leaderboard")]);
    if (state.dailyNumber) $("daily-board-title").textContent = `Daily #${state.dailyNumber}`;
    fillLeaders($("daily-leaders"), today);
    fillLeaders($("leaders"), allTime);
  } catch (err) {
    toast(err.message);
  }
}

// --- wiring -----------------------------------------------------------------------

function init() {
  buildKeyboard();
  // Rotating the phone or the address bar sliding away changes the space available.
  window.addEventListener("resize", fitBoard);
  window.visualViewport?.addEventListener("resize", fitBoard);
  state.player = store.get("player");
  $("player").value = state.player;

  api("/api/daily").then((info) => {
    state.dailyNumber = info.number;
    $("daily-btn").textContent = `Daily #${info.number}`;
  }).catch(() => {});

  $("start-form").addEventListener("submit", (e) => {
    e.preventDefault();
    start(e.submitter?.value === "practice" ? "practice" : "daily");
  });

  $("keyboard").addEventListener("click", (e) => {
    const key = e.target.closest(".key");
    if (key) press(key.dataset.key);
  });

  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.target.matches("input")) return;
    if (e.key === "Enter" || e.key === "Backspace" || /^[a-zA-Z]$/.test(e.key)) {
      if (state.game) e.preventDefault();
      // A focused on-screen key would also "click" on Enter, so don't let it.
      if (e.target.closest?.(".key")) e.target.blur();
      press(e.key.length === 1 ? e.key.toLowerCase() : e.key);
    }
  });

  $("help-btn").addEventListener("click", () => $("help-dialog").showModal());
  $("stats-btn").addEventListener("click", openStats);
  $("boards-btn").addEventListener("click", openBoards);
  $("share-btn").addEventListener("click", share);
  $("again-btn").addEventListener("click", () => {
    $("stats-dialog").close();
    start("practice");
  });

  for (const dlg of document.querySelectorAll("dialog")) {
    dlg.querySelector(".close").addEventListener("click", () => dlg.close());
    // Tapping the backdrop closes it too. (The backdrop counts as the dialog itself, so
    // check where the tap landed rather than what was tapped.)
    dlg.addEventListener("click", (e) => {
      const r = dlg.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (e.target === dlg && !inside) dlg.close();
    });
  }
  $("stats-dialog").addEventListener("close", () => clearInterval(countdownTimer));

  // First visit: show the rules once.
  if (!store.get("seen-help")) {
    store.set("seen-help", "1");
    $("help-dialog").showModal();
  }
}

init();
