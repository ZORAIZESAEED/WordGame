resource "aws_db_subnet_group" "main" {
  name       = var.project
  subnet_ids = aws_subnet.private[*].id
}

# Only URL-safe characters, since the password goes straight into DATABASE_URL.
# It ends up in Terraform state, which is why the state bucket is private and encrypted.
resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_db_instance" "main" {
  identifier     = var.project
  engine         = "postgres"
  engine_version = "16" # matches docker-compose

  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  multi_az               = false
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  db_name  = "wordgame"
  username = "wordgame"
  password = random_password.db.result

  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  deletion_protection        = false
  skip_final_snapshot        = var.db_skip_final_snapshot
  final_snapshot_identifier  = var.db_skip_final_snapshot ? null : "${var.project}-final"
}

# The app reads one DATABASE_URL, so store it whole. ECS injects it at task start.
resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.project}/database_url"
  type  = "SecureString"
  value = "postgresql+psycopg://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
}

# Seeds the daily-word schedule (app/daily.py). Without it the app falls back to a default
# that's in the public repo, so anyone could work out upcoming daily words.
resource "random_password" "daily_word" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "daily_word_secret" {
  name  = "/${var.project}/daily_word_secret"
  type  = "SecureString"
  value = random_password.daily_word.result
}
