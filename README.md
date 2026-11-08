# Word Game

A five-letter word guessing game with a FastAPI backend, a tiny browser frontend,
and a leaderboard. Built as a learning project for AWS and CI/CD.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 to play, or http://localhost:8000/docs for the API.

## Run it with Docker (Postgres + API)

```bash
docker compose up --build
```

## Tests and lint

```bash
ruff check .
pytest
```

## Roadmap

- [x] Game logic, API, leaderboard, tests
- [x] Dockerfile and compose
- [x] CI: lint, test, build image (GitHub Actions)
- [ ] Terraform: VPC, ECR, ECS Fargate, RDS, ALB
- [ ] CD: push image to ECR and deploy on merge to main (OIDC, no stored AWS keys)
- [ ] Daily word, accounts
- [ ] RL opponent that plays the game
