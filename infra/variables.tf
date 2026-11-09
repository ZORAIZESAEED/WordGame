variable "region" {
  description = "AWS region. London by default."
  type        = string
  default     = "eu-west-2"
}

variable "project" {
  description = "Name used in resource names and tags."
  type        = string
  default     = "wordgame"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "image_tag" {
  description = "Tag of the image in ECR that the ECS service runs."
  type        = string
  default     = "latest"
}

variable "desired_count" {
  description = "How many app tasks to run. Set to 0 to stop paying for Fargate."
  type        = number
  default     = 1
}

variable "task_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)."
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "db_instance_class" {
  description = "RDS instance size."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage in GiB."
  type        = number
  default     = 20
}

variable "db_skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Fine for a demo, not for real data."
  type        = bool
  default     = true
}
