# Word Game: project context for Claude Code

Owner: Zoraize Saeed. Goal: a small, finished project that shows AWS + DevOps skills
(FastAPI app, Docker, CI/CD, Terraform on AWS) for UK junior AI/software engineer job applications.
The game is a vehicle for the infrastructure work, so keep the app simple.

## Current state
- FastAPI backend in `app/` (game logic in `game.py`, no web code in it), SQLAlchemy models,
  SQLite locally and Postgres via `DATABASE_URL`.
- Static frontend in `static/index.html`.
- 16 passing tests in `tests/`, ruff lint config in `pyproject.toml`. `pythonpath = ["."]`
  in the pytest config is what lets a bare `pytest` import `app`, so keep it.
- Dockerfile + docker-compose (api + Postgres). The image builds, passes the `/health`
  smoke test, and works against Postgres 16.
- GitHub Actions CI in `.github/workflows/ci.yml` (lint, test, build image, smoke test).
  Green on `main`.

## Cloud sessions
- The "WordGame" cloud environment's setup script creates `.venv` (Python 3.12) with
  `requirements-dev.txt` installed, so use `.venv/bin/pytest` and `.venv/bin/ruff`.
- Docker is installed but the daemon isn't running at start: run `dockerd` in the background first.
- Builds there need `--network host`, and pip inside the container doesn't trust the sandbox's
  proxy certificate. Work around that with a throwaway Dockerfile copy that adds
  `/root/.ccr/ca-bundle.crt` and sets `PIP_CERT`. Don't commit that to the real Dockerfile.
- No AWS credentials in the environment yet. Add them before running `terraform plan` there.

## Commands
- Run: `uvicorn app.main:app --reload`
- Test: `pytest -q`   Lint: `ruff check .`
- Full stack: `docker compose up --build`

## Next steps, in order
1. Terraform in `infra/`: VPC, ECR, ECS Fargate, RDS Postgres, ALB. Budget alert first.
2. CD workflow: build and push to ECR, deploy to ECS on merge to main, using GitHub OIDC
   (no long-lived AWS keys stored in the repo).
3. Later: daily word, accounts, RL opponent (links to the user's MSc research on word acquisition).

## Preferences
- Write README and docs text in a natural, human voice, not stiff or generic.
- Never commit secrets, .env files, or Terraform state.
