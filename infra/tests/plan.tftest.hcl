# Plans the stack against mocked providers, so it runs in CI without AWS credentials.
# Run from infra/: terraform init -backend=false && terraform test

mock_provider "aws" {
  # Mocks make up random strings, but some arguments must look like real ARNs.
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-2:123456789012:loadbalancer/app/wordgame/0123456789abcdef" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:eu-west-2:123456789012:targetgroup/wordgame/0123456789abcdef" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/mock" }
  }
  mock_resource "aws_ssm_parameter" {
    defaults = { arn = "arn:aws:ssm:eu-west-2:123456789012:parameter/wordgame/mock" }
  }

  override_data {
    target = data.aws_availability_zones.available
    values = {
      names = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
    }
  }

  override_data {
    target = data.aws_iam_policy_document.ecs_tasks_assume
    values = { json = "{}" }
  }

  override_data {
    target = data.aws_iam_policy_document.execution_secrets
    values = { json = "{}" }
  }
}

mock_provider "random" {}

run "plan_defaults" {
  command = plan

  assert {
    condition     = length(aws_subnet.public) == 2 && length(aws_subnet.private) == 2
    error_message = "Expected two public and two private subnets."
  }

  assert {
    condition     = aws_subnet.private[0].cidr_block == "10.20.10.0/24"
    error_message = "Private subnet CIDRs moved."
  }

  assert {
    condition     = aws_db_instance.main.publicly_accessible == false && aws_db_instance.main.storage_encrypted
    error_message = "The database must be private and encrypted."
  }

  assert {
    condition     = aws_ecs_service.app.network_configuration[0].assign_public_ip
    error_message = "Without a NAT gateway, tasks need a public IP to pull from ECR."
  }

  assert {
    condition     = aws_lb_target_group.app.health_check[0].path == "/health"
    error_message = "ALB health check should hit /health."
  }
}

run "scale_to_zero" {
  command = plan

  variables {
    desired_count = 0
  }

  assert {
    condition     = aws_ecs_service.app.desired_count == 0
    error_message = "desired_count should pass through to the service."
  }
}

# The container definitions hold ARNs that only exist after an apply, so this one needs
# command = apply. With mock providers that "apply" happens entirely in memory: nothing is
# created in AWS and no credentials are used.
run "secrets_reach_the_container" {
  command = apply

  assert {
    condition     = toset([for s in jsondecode(aws_ecs_task_definition.app.container_definitions)[0].secrets : s.name]) == toset(["DATABASE_URL", "DAILY_WORD_SECRET"])
    error_message = "The app needs DATABASE_URL and its own DAILY_WORD_SECRET (or daily words are guessable from the repo)."
  }
}
