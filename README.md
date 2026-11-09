# Word Game

[![CI](https://github.com/ZORAIZESAEED/WordGame/actions/workflows/ci.yml/badge.svg)](https://github.com/ZORAIZESAEED/WordGame/actions/workflows/ci.yml)

A five-letter word guessing game: six tries, coloured hints after each guess, and a
leaderboard. Under the hood it's a FastAPI backend with Postgres, a mobile-first frontend,
Docker, a GitHub Actions pipeline, and Terraform for running it on AWS.

I built it as a learning project for backend and DevOps work, so the game is deliberately
simple and most of the effort goes into how it's built, tested and shipped.

## Run it

You need Docker. This starts the API and a Postgres 16 database:

```bash
docker compose up --build
```

Open http://localhost:8000 to play, or http://localhost:8000/docs for the interactive API docs.
Games are stored in a Docker volume, so they survive a restart. `docker compose down -v`
wipes them.

### Without Docker

Python 3.12 or newer. The app falls back to a local SQLite file when there's no `DATABASE_URL`.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## How to play

Enter a name and pick a mode:

- **Daily**: everyone gets the same word, and there's a new one at midnight UTC. One go per
  name per day; come back later with the same name and you pick up where you left off.
- **Practice**: a random word every time, as many games as you like.

After each guess every letter is marked:

- **green**: right letter, right place
- **yellow**: in the word, but somewhere else
- **grey**: not in the word (repeated letters are only marked as often as they appear)

Win on the first guess for 600 points, down to 100 on the sixth. Daily wins go on today's
leaderboard, and every win counts towards the all-time one.

It's built for phones first: the tiles size themselves to the screen, there's an on-screen
keyboard that colours in letters as you learn about them, and a physical keyboard works too.
When a game ends you get your stats (games played, win rate, current and best daily streak,
and how many guesses your wins took), a countdown to the next daily, and a **Share** button
that copies a spoiler-free grid of coloured squares. Animations are switched off for anyone
who has asked their device for reduced motion.

## API

| Method | Path | What it does |
| --- | --- | --- |
| `POST` | `/api/games` | Start a practice game: `{"player": "name"}` |
| `GET` | `/api/daily` | Today's puzzle number and date (never the word) |
| `POST` | `/api/daily` | Start today's daily, or resume it: `{"player": "name"}`. 201 when new, 200 when resuming |
| `GET` | `/api/daily/leaderboard?limit=10` | Today's daily winners |
| `GET` | `/api/games/{id}` | Current state of a game |
| `POST` | `/api/games/{id}/guesses` | Guess a word: `{"word": "crane"}` |
| `GET` | `/api/leaderboard?limit=10` | All-time top scores |
| `GET` | `/api/players/{name}/stats` | Daily stats (played, win %, streaks, guess distribution) and practice totals |
| `GET` | `/health` | Health check for load balancers and Docker |

The answer is never sent while a game is in progress.

## Configuration

| Variable | Default | What it's for |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./wordgame.db` | Where games are stored. Compose sets it to its Postgres. |
| `DAILY_WORD_SECRET` | a fixed dev value | Seeds the daily-word schedule. Set your own anywhere public, or people reading this repo can work out upcoming words. |

## Tests

```bash
ruff check .            # lint
ruff format --check .   # formatting
pytest -q               # unit and API tests on SQLite
```

To run the same tests against Postgres, start one and point `TEST_DATABASE_URL` at it.
(It's a separate variable from `DATABASE_URL` on purpose: the tests drop every table.)

```bash
docker run -d --rm --name pgtest -p 55432:5432 -e POSTGRES_USER=wordgame \
  -e POSTGRES_PASSWORD=wordgame -e POSTGRES_DB=wordgame_test postgres:16-alpine
TEST_DATABASE_URL=postgresql+psycopg://wordgame:wordgame@localhost:55432/wordgame_test pytest -q
docker stop pgtest
```

There's also an end-to-end smoke test that plays a round against a running server. With
`docker compose up` running:

```bash
python scripts/smoke_test.py
```

And browser tests in `e2e/`, which start the app themselves (on a throwaway SQLite database)
and play it in Chromium on a phone-sized screen: typing on the on-screen and real keyboards,
error messages, winning, stats, sharing, resuming a daily, and fitting on a small phone.

```bash
pip install -r requirements-e2e.txt
python -m playwright install chromium
pytest e2e
```

## CI

Every push to `main` and every pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
None of it needs AWS credentials or any other secret.

- **test**: ruff, then the test suite on SQLite and again on a Postgres 16 service container
- **e2e**: the browser tests, in headless Chromium
- **terraform**: `fmt`, `validate`, and `terraform test`, which plans the AWS stack against mocked providers
- **docker**: builds the image, starts the full compose stack, and runs the smoke test

## Database migrations

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/), with migrations in
`app/migrations/versions/`. The app applies any pending ones when it starts, so `uvicorn`,
`docker compose` and the tests all just work. A database created by an older version of
the app (before migrations) is picked up automatically.

When you change a model in `app/models.py`, write a migration to match:

```bash
alembic revision --autogenerate --rev-id 0002 -m "describe the change"
```

Read what it generated before committing. `tests/test_migrations.py` fails if the models
and migrations ever disagree, so a forgotten migration shows up in CI.

## Word lists

Answers come from `app/data/answers.txt`: 864 common, family-friendly words in British
spelling, picked by hand. Guesses are checked against `app/data/allowed.txt`, about 4,700
five-letter words from the British and American lists in
[SCOWL](http://wordlist.aspell.net/) (Kevin Atkinson and contributors), so either
spelling works. SCOWL's license is in `app/data/SCOWL-LICENSE.txt`.

## Deployment

**It isn't deployed right now, on purpose.** The AWS setup in [`infra/`](infra/) works on
paper (validated and plan-tested in CI), but it costs around $50–60 a month just to exist,
which isn't worth it for a demo nobody's using yet.

What's there: a budget alert and Terraform state bucket (`infra/bootstrap/`), then a VPC, ECR,
ECS Fargate, RDS Postgres and an Application Load Balancer. [`infra/README.md`](infra/README.md)
has the step-by-step for when it's time, and [`docs/architecture.md`](docs/architecture.md)
covers the costs, cheaper hosting options, and what I'd change.

The app itself only needs a container runtime and a `DATABASE_URL`, so it'll run on most
hosts that run Docker.

## Project layout

```
app/            FastAPI app: main.py (routes), game.py (rules), models.py, db.py, words.py
app/data/       word lists: answers.txt (hand-picked) and allowed.txt (dictionary)
app/migrations/ Alembic migrations, applied on startup by app/migrate.py
static/         the frontend: index.html, style.css, app.js (no build step, no libraries)
tests/          pytest: game logic, API, stats, migrations, concurrency
e2e/            browser tests with Playwright
scripts/        smoke_test.py, an end-to-end check against a running server
infra/          Terraform for AWS (not applied), with its own tests
docs/           architecture notes and review
```

## Roadmap

- [x] Game logic, API, leaderboard, tests
- [x] Dockerfile and compose (API + Postgres)
- [x] CI: lint, tests on SQLite and Postgres, compose smoke test
- [x] Terraform for AWS: VPC, ECR, ECS Fargate, RDS, ALB, budget alert (written and tested, not applied)
- [x] Bigger word list: 864 hand-picked answers, about 4,700 accepted guesses
- [x] Daily challenge (same word for everyone, one go per day) plus unlimited practice
- [x] Database migrations with Alembic
- [x] Simultaneous guesses can't get past the six-attempt limit
- [x] Mobile-first UI: on-screen keyboard, animations, stats, streaks, sharing, browser tests
- [ ] Low-cost live demo
- [ ] CD: build, push and deploy on merge to main (GitHub OIDC, no stored keys)
- [ ] Accounts
- [ ] An RL opponent that plays the game
