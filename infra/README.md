# Infrastructure

> **Not deployed, and costs money if you deploy it.** Everything here has been checked with
> `terraform validate` and `terraform test` (mocked AWS, run in CI), but never applied.
> `terraform apply` on the main stack creates resources that bill by the hour, around
> $50–60 a month in total. See [`../docs/architecture.md`](../docs/architecture.md) for
> cheaper options.

Terraform for running Word Game on AWS (London, `eu-west-2`). Two stacks:

- `bootstrap/` runs once, with local state. It sets up a monthly **budget alert** on the
  account and the S3 bucket that holds state for everything else.
- `infra/` itself is the app: VPC, ECR, ECS Fargate, RDS Postgres and an Application Load Balancer.

```
internet ──► ALB (public subnets, :80)
               │
               ▼
         Fargate task (public subnets, only accepts traffic from the ALB, :8000)
               │
               ▼
         RDS Postgres 16 (private subnets, only accepts traffic from the app, :5432)
```

## A note on cost

There's no NAT gateway. It would cost about as much as everything else put together,
so the Fargate task sits in a public subnet with a public IP and pulls its image from
ECR directly. Its security group still only lets the load balancer in.

Running all the time, expect somewhere around **$50–60 a month**. The load balancer, the
small RDS instance and the public IPv4 addresses make up most of it. Check the AWS pricing
pages for current numbers. To stop paying for it between demos:

- `terraform apply -var desired_count=0` stops the app containers, or
- `terraform destroy` removes the whole app stack. The state bucket and budget stay.

## First-time setup

You need the AWS CLI logged in to your account (`aws sts get-caller-identity` should work)
and Terraform 1.10 or newer.

**1. Budget and state bucket**

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # put your email in it
terraform init
terraform apply
```

AWS emails you to confirm the budget alert subscription. Click the link, or the alerts
go nowhere. Keep `bootstrap/terraform.tfstate` somewhere safe. It's tiny, but it's the only
record of the bucket and budget.

**2. Point the main stack at the bucket**

```bash
cd ..
cp backend.hcl.example backend.hcl   # set bucket to the state_bucket output from step 1
terraform init -backend-config=backend.hcl
```

**3. Create the image repository and push an image**

ECS can't start the service until there's an image to run, so create ECR on its own first:

```bash
terraform apply -target=aws_ecr_repository.app
REPO=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin "${REPO%/*}"
docker build --platform linux/amd64 -t "$REPO:latest" ..
docker push "$REPO:latest"
```

**4. Everything else**

```bash
terraform apply
terraform output app_url
```

RDS takes about ten minutes to come up. Once the target group reports the task as healthy,
the URL serves the game.

## How the database password works

Terraform generates the password, builds the full `DATABASE_URL` and stores it in SSM
Parameter Store as a SecureString. ECS reads it when a task starts and passes it to the
container as an environment variable, so the app code doesn't change. The password does
end up in Terraform state, which is why the state bucket is private, encrypted and versioned.

## Tests

`tests/plan.tftest.hcl` plans the stack against mocked providers and checks a few things
that matter (the database is private, subnets haven't shifted, and so on). It needs no AWS
credentials, so CI runs it on every push:

```bash
terraform init -backend=false
terraform test
```

## Not done yet

- HTTPS. That needs a domain and an ACM certificate.
- CD: GitHub Actions pushing to ECR and deploying to ECS, using OIDC rather than stored keys.
