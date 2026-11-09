output "state_bucket" {
  description = "Put this in infra/backend.hcl."
  value       = aws_s3_bucket.tfstate.bucket
}

output "region" {
  value = var.region
}
