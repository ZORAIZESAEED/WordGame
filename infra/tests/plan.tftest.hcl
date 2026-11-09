# Plans the stack against mocked providers, so it runs in CI without AWS credentials.
# Run from infra/: terraform init -backend=false && terraform test

mock_provider "aws" {
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
