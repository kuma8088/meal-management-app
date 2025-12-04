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
