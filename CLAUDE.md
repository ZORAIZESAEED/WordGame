# Word Game: project context for Claude Code

Owner: Zoraize Saeed. Goal: a small, finished project that shows AWS + DevOps skills
(FastAPI app, Docker, CI/CD, Terraform on AWS) for UK junior AI/software engineer job applications.
The game is a vehicle for the infrastructure work, so keep the app simple.

## Current state
- FastAPI backend in `app/` (game logic in `game.py`, no web code in it), SQLAlchemy models,
  SQLite locally and Postgres via `DATABASE_URL`.
- Static frontend in `static/index.html`.
- 16 passing tests in `tests/`, ruff lint config in `pyproject.toml`.
- Dockerfile + docker-compose (api + Postgres). The image has NOT been built yet
  (the earlier environment had no Docker daemon), so verify it first.
- GitHub Actions CI in `.github/workflows/ci.yml` (lint, test, build image, smoke test). Not run yet.

## Commands
- Run: `uvicorn app.main:app --reload`
- Test: `pytest -q`   Lint: `ruff check .`
- Full stack: `docker compose up --build`

## Next steps, in order
1. Create the GitHub repo, push, confirm CI goes green.
2. Terraform in `infra/`: VPC, ECR, ECS Fargate, RDS Postgres, ALB. Budget alert first.
3. CD workflow: build and push to ECR, deploy to ECS on merge to main, using GitHub OIDC
   (no long-lived AWS keys stored in the repo).
4. Later: daily word, accounts, RL opponent (links to the user's MSc research on word acquisition).

## Preferences
- Write README and docs text in a natural, human voice, not stiff or generic.
- Never commit secrets, .env files, or Terraform state.
