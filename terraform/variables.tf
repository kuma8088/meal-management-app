variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "meal-management-app"
}

variable "line_channel_secret" {
  description = "LINE Messaging API Channel Secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "line_channel_access_token" {
  description = "LINE Messaging API Channel Access Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "alert_email" {
  description = "Email address for CloudWatch Alarms notifications"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch Logs retention period."
  }
}
