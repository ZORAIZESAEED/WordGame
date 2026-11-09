# Architecture and review

This is a look at how Word Game is put together, what each piece costs, and what I'd
cut or change. The short version: the app is in good shape and cheap to run anywhere.
The AWS design is sound but costs real money every hour it exists, so it stays in the
repo as code and isn't deployed.

## How it fits together

```
browser ──► FastAPI (app/main.py) ──► SQLAlchemy ──► SQLite (dev, tests)
            │                                   └─► Postgres (docker compose, CI, AWS)
            ├─ serves static/index.html
            └─ game rules live in app/game.py (no web or database code)
```

- **Game logic** is pure Python in `app/game.py`, so it's tested without a server or database.
- **The API** keeps the secret word on the server. A game's answer only appears in the
  response once the game is over.
- **One setting switches the database.** `DATABASE_URL` picks SQLite or Postgres, and the same
  code and tests run on both. CI runs the test suite against each.
- **The frontend** is one HTML file with no build step.

## Where it runs today

| Where | What runs | Cost |
| --- | --- | --- |
| Your machine, `uvicorn` | API + SQLite | free |
| Your machine, `docker compose` | API container + Postgres 16 | free |
| GitHub Actions | lint, tests on SQLite and Postgres, compose smoke test, Terraform checks | free for public repos |
| AWS | nothing: Terraform written and tested, never applied | $0 |

## The AWS design (in `infra/`, not deployed)

ALB → ECS Fargate → RDS Postgres, in a VPC across two availability zones, with ECR for images
and a budget alert set up before anything else.

Choices that keep it cheaper and simpler than the "textbook" version:

- **No NAT gateway.** Tasks run in public subnets with public IPs, locked down so only the load
  balancer can reach them. A NAT gateway would cost about as much as the rest put together.
- **Single-AZ RDS, smallest instance.** Fine for a demo; multi-AZ would double the database cost.
- **HTTP only.** HTTPS needs a domain and certificate, which isn't worth it before there's
  anything to show.
- **No autoscaling, WAF, or Container Insights.** None of them earn their cost at this size.

### What it would cost

Most of the bill is fixed hourly charges that you pay whether or not anyone plays. Rough
monthly figures for London, running all the time (check the AWS pricing pages for current numbers):

| Piece | Roughly |
| --- | --- |
| Application Load Balancer | $18–20 |
| RDS `db.t4g.micro` + 20 GB | $15 |
| Fargate, 0.25 vCPU / 0.5 GB | $9–10 |
| Public IPv4 addresses (ALB ×2, task ×1) | $11 |
| ECR, logs, SSM, S3 state | under $1 |
| **Total** | **about $50–60** |

That's a lot for a portfolio piece nobody's using. Hence the rule for now: don't run
`terraform apply`.

## Suggestions

### Cost and hosting

1. **Keep the Terraform as code, don't apply it yet.** For job applications, readable, tested
   Terraform with a CI check shows most of what a deployed stack would. Done: CI validates it
   and plans it against mocked AWS on every push.
2. **When you want a live demo, go small first.** Options, cheapest first:
   - A container host with a free or hobby tier, plus a free hosted Postgres (Neon, Supabase and
     similar). Free tiers change often, so check current terms, and expect cold starts.
     `DATABASE_URL` is the only thing the app needs.
   - One small EC2 or Lightsail instance running the existing `docker-compose.yml`. A few dollars
     a month, still "on AWS" for your CV, and the Terraform shrinks to an instance, a security
     group and an elastic IP.
   - The full Fargate stack, if you want to demo it for an interview, then `terraform destroy`.
     At roughly 8 cents an hour, an afternoon costs well under a dollar.
3. **Keep the bootstrap stack even if you never deploy the app.** Basic budget alerts cost nothing
   and are the right first thing to create in any AWS account.

### Complexity worth questioning

4. **Two Terraform stacks plus an S3 backend** is the standard pattern, but it's the most moving
   parts for a first apply. It's worth keeping because it's what real teams do. If you go the
   single-instance route, local state is fine.
5. **ECS service before an image exists.** First-time setup needs a targeted apply for ECR,
   then an image push, then the full apply. CD would remove the manual step.

### App and code quality

6. **Migrations.** Tables are created with `create_all` at startup. That's fine until the schema
   changes (daily word, accounts). Adding Alembic then would be a good thing to show.
7. **Concurrent guesses.** Two requests for the same game at the same moment could both pass the
   "six attempts" check. Locking the row (`with_for_update()` in SQLAlchemy) fixes it on Postgres.
   Low priority for a single-player game.
8. **Pinned dependencies.** `requirements*.txt` use version ranges, so CI can pick up a new
   release overnight. A lock file (`uv pip compile` or `pip-tools`) makes builds repeatable.
9. **Word list.** 80 answers repeat quickly. Loading a few thousand from a file is a small change
   with a big effect on the game.
10. **Leaderboard abuse.** Anyone can post any name and as many games as they like. Fine for a
    demo; rate limiting or accounts would matter once it's public.

### Fixed in this round

- A name of only spaces passed validation and was saved as an empty string. It's now rejected.
- Validation errors showed up as `[object Object]` in the browser. They now show the message.
- The leaderboard built HTML from player names. It now uses `textContent`.
- Tests could only run on SQLite. `TEST_DATABASE_URL` points them at Postgres, and CI does both.
- CI's container check only hit `/health`. It now starts the compose stack and plays a round.
