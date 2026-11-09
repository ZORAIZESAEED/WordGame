variable "region" {
  description = "AWS region for the state bucket."
  type        = string
  default     = "eu-west-2"
}

variable "project" {
  description = "Name used in resource names and tags."
  type        = string
  default     = "wordgame"
}

variable "alert_email" {
  description = "Where budget alerts go. AWS sends a confirmation email first."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget for the whole account, in USD."
  type        = number
  default     = 50
}
