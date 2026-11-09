# Word Game: project context for Claude Code

Owner: Zoraize Saeed. Goal: a small, finished project that shows AWS + DevOps skills
(FastAPI app, Docker, CI/CD, Terraform on AWS) for UK junior AI/software engineer job applications.
The game is a vehicle for the infrastructure work, so keep the app simple.

## Ground rules (from the owner)
- Never run `terraform apply` or create any paid AWS resource without the owner's explicit
  approval in the conversation. `terraform validate`, `terraform test` and `fmt` are fine.
- Avoid AWS charges for now. The game must run fully locally (Docker + Postgres), and CI must
  keep passing without AWS credentials or other secrets.
- Priorities: game functionality, code quality, tests, docs. A free or low-cost live demo
  may come later (options in `docs/architecture.md`).
- Changes go through pull requests, not straight to `main`.

## Current state
- FastAPI backend in `app/` (game logic in `game.py`, no web code in it), SQLAlchemy models,
  SQLite locally and Postgres via `DATABASE_URL`.
- Static frontend in `static/index.html`.
- Tests in `tests/` run on SQLite by default; set `TEST_DATABASE_URL` for Postgres (never
  `DATABASE_URL`: the tests drop all tables). `pythonpath = ["."]` in the pytest config is what
  lets a bare `pytest` import `app`, so keep it. CI runs `ruff check` and `ruff format --check`.
- Guessing locks the game row (`_get_game(..., lock=True)`); SQLite uses `BEGIN IMMEDIATE`
  (see `app/db.py`). Keep any new read-then-write endpoint behind the same lock.
  `tests/test_concurrency.py` checks it with real threads.
- Schema changes need an Alembic migration (`alembic revision --autogenerate --rev-id 000N -m ...`,
  then review it). The app runs `upgrade_to_head` on startup (`app/migrate.py`).
  `tests/test_migrations.py` fails if models and migrations differ. The test reset also drops
  `alembic_version`.
- Word lists live in `app/data/`: `answers.txt` (hand-picked, British spelling, family-friendly)
  and `allowed.txt` (SCOWL British + American five-letter words; keep `SCOWL-LICENSE.txt` with it).
- Dockerfile + docker-compose (api + Postgres, both with healthchecks). `scripts/smoke_test.py`
  plays a round against a running server.
- GitHub Actions CI in `.github/workflows/ci.yml`: ruff + pytest on SQLite and Postgres;
  Terraform fmt/validate/test (mocked, no credentials); compose stack + smoke test.
- `docs/architecture.md` has the architecture review, cost table and open suggestions.
- Terraform in `infra/` (see `infra/README.md`): `bootstrap/` = budget alert + S3 state bucket;
  main stack = VPC, ECR, ECS Fargate, RDS, ALB. Validated and plan-tested with mocks,
  NOT applied to AWS yet. No NAT gateway on purpose (cost); tasks get public IPs.

## Cloud sessions
- The "WordGame" cloud environment's setup script creates `.venv` (Python 3.12) with
  `requirements-dev.txt` installed, so use `.venv/bin/pytest` and `.venv/bin/ruff`.
- Docker is installed but the daemon isn't running at start: run `dockerd` in the background first.
- Builds there need `--network host`, and pip inside the container doesn't trust the sandbox's
  proxy certificate. Work around that with a throwaway Dockerfile copy that adds
  `/root/.ccr/ca-bundle.crt` and sets `PIP_CERT`. Don't commit that to the real Dockerfile.
- Terraform isn't preinstalled: get it from releases.hashicorp.com (checksum it). The environment
  allows registry.terraform.io for providers. Set `CHECKPOINT_DISABLE=1` (its telemetry host is blocked).
- No AWS credentials in the environment yet. Add them before running `terraform plan` there.

## Commands
- Run: `uvicorn app.main:app --reload`
- Test: `pytest -q`   Lint: `ruff check .`
- Full stack: `docker compose up --build`

## Next steps, in order
1. One branch and one PR (with tests) per feature, in this order: daily challenge + practice mode;
   mobile UI, animations, on-screen keyboard, stats and sharing. Pinned dependencies when
   convenient (see `docs/architecture.md`).
2. Later, with approval: a free or low-cost live demo. Applying `infra/` (bootstrap first, for
   the budget) and a CD workflow with GitHub OIDC only if the owner asks.
3. Later: daily word, accounts, RL opponent (links to the user's MSc research on word acquisition).

## Preferences
- Write README and docs text in a natural, human voice, not stiff or generic.
- Never commit secrets, .env files, or Terraform state.
