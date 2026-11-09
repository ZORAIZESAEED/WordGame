# Word Game

[![CI](https://github.com/ZORAIZESAEED/WordGame/actions/workflows/ci.yml/badge.svg)](https://github.com/ZORAIZESAEED/WordGame/actions/workflows/ci.yml)

A five-letter word guessing game: six tries, coloured hints after each guess, and a
leaderboard. Under the hood it's a FastAPI backend with Postgres, a single-page frontend,
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

Enter a name and start guessing. After each guess every letter is marked:

- **green**: right letter, right place
- **yellow**: in the word, but somewhere else
- **grey**: not in the word (repeated letters are only marked as often as they appear)

Win on the first guess for 600 points, down to 100 on the sixth. Wins go on the leaderboard.

## API

| Method | Path | What it does |
| --- | --- | --- |
| `POST` | `/api/games` | Start a game: `{"player": "name"}` |
| `GET` | `/api/games/{id}` | Current state of a game |
| `POST` | `/api/games/{id}/guesses` | Guess a word: `{"word": "crane"}` |
| `GET` | `/api/leaderboard?limit=10` | Top scores |
| `GET` | `/health` | Health check for load balancers and Docker |

The answer is never sent while a game is in progress.

## Tests

```bash
ruff check .            # lint
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

## CI

Every push to `main` and every pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
None of it needs AWS credentials or any other secret.

- **test**: ruff, then the test suite on SQLite and again on a Postgres 16 service container
- **terraform**: `fmt`, `validate`, and `terraform test`, which plans the AWS stack against mocked providers
- **docker**: builds the image, starts the full compose stack, and runs the smoke test

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
static/         the frontend (one HTML file)
tests/          pytest: game logic and API
scripts/        smoke_test.py, an end-to-end check against a running server
infra/          Terraform for AWS (not applied), with its own tests
docs/           architecture notes and review
```

## Roadmap

- [x] Game logic, API, leaderboard, tests
- [x] Dockerfile and compose (API + Postgres)
- [x] CI: lint, tests on SQLite and Postgres, compose smoke test
- [x] Terraform for AWS: VPC, ECR, ECS Fargate, RDS, ALB, budget alert (written and tested, not applied)
- [ ] Bigger word list and a daily word
- [ ] Database migrations with Alembic
- [ ] Low-cost live demo
- [ ] CD: build, push and deploy on merge to main (GitHub OIDC, no stored keys)
- [ ] Accounts
- [ ] An RL opponent that plays the game
