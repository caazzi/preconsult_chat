variable "aws_region" {
  description = "Region for the VPC, ALB, ECR, ECS and CloudWatch resources. May differ from var.llm_region (Bedrock is a regional service)."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Resource name prefix."
  type        = string
  default     = "preconsult"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,11}$", var.project_name))
    error_message = "project_name must be 2-12 lowercase alphanumeric/dash characters (ALB and target-group names are capped at 32)."
  }
}

variable "environment" {
  description = "Deployment environment, used in resource names and tags."
  type        = string
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,11}$", var.environment))
    error_message = "environment must be 2-12 lowercase alphanumeric/dash characters."
  }
}

variable "image" {
  description = "Full container image reference to deploy (ECR repository URL plus an immutable tag or digest). Deliberately has no default: a forgotten image must fail, not silently deploy a stale build."
  type        = string
}

variable "container_port" {
  description = "Port the container listens on. gunicorn binds $PORT, which the task definition sets to this value."
  type        = number
  default     = 8080
}

variable "vpc_cidr" {
  description = "CIDR for the VPC. Two public /24 subnets are carved out of it."
  type        = string
  default     = "10.20.0.0/16"

  validation {
    condition     = can(cidrsubnet(var.vpc_cidr, 8, 1))
    error_message = "vpc_cidr must be a valid IPv4 CIDR with at least 8 bits left to split (prefix length <= 24)."
  }
}

# --- Provider / model (parity with the app's config.py defaults) -----------

variable "llm_provider" {
  description = "LLM_PROVIDER passed to the container."
  type        = string
  default     = "bedrock"
}

variable "llm_model" {
  description = "Bedrock model or cross-region inference-profile id passed as LLM_MODEL; also the inference-profile resource in the task role policy."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "llm_foundation_model_id" {
  description = "Underlying foundation model id (no us./eu./apac. geography prefix) that var.llm_model routes to. Cross-region profiles need invoke permission on the model ARN in every destination region."
  type        = string
  default     = "anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "llm_region" {
  description = "Bedrock region passed as LLM_REGION. Fixed on purpose: data residency must not be routed by the UI language."
  type        = string
  default     = "us-east-1"
}

# --- SSM parameters that hold secrets (names only, never values) -----------

variable "redis_url_param_name" {
  description = "SSM SecureString parameter name holding the Upstash REDIS_URL."
  type        = string
  default     = "/preconsult/prod/REDIS_URL"

  validation {
    condition     = startswith(var.redis_url_param_name, "/")
    error_message = "SSM parameter names used in ARNs must start with '/'."
  }
}

variable "preconsult_api_key_param_name" {
  description = "SSM SecureString parameter name holding PRECONSULT_API_KEY."
  type        = string
  default     = "/preconsult/prod/PRECONSULT_API_KEY"

  validation {
    condition     = startswith(var.preconsult_api_key_param_name, "/")
    error_message = "SSM parameter names used in ARNs must start with '/'."
  }
}

variable "session_secret_param_name" {
  description = "SSM SecureString parameter name holding SESSION_SECRET (cookie signing key)."
  type        = string
  default     = "/preconsult/prod/SESSION_SECRET"

  validation {
    condition     = startswith(var.session_secret_param_name, "/")
    error_message = "SSM parameter names used in ARNs must start with '/'."
  }
}

# --- Compute / scaling -----------------------------------------------------

variable "cpu" {
  description = "Fargate task CPU units (512 = 0.5 vCPU, matching the current Cloud Run cost profile)."
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Initial task count. Autoscaling owns this value afterwards."
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Autoscaling floor. One warm task avoids a cold-start on every request."
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Autoscaling ceiling (parity with the Cloud Run max instance cap)."
  type        = number
  default     = 5
}

variable "cpu_target_utilization" {
  description = "Target-tracking CPU percentage that drives scaling."
  type        = number
  default     = 60
}

variable "health_check_grace_period_seconds" {
  description = "Grace period before ECS starts failing a task on ALB health checks. The measured cold import is ~70s."
  type        = number
  default     = 120
}

# --- Edge ------------------------------------------------------------------

variable "alb_idle_timeout" {
  description = "ALB idle timeout in seconds. Must comfortably exceed the gap between SSE events."
  type        = number
  default     = 300

  validation {
    condition     = var.alb_idle_timeout >= 1 && var.alb_idle_timeout <= 4000
    error_message = "ALB idle_timeout must be between 1 and 4000 seconds."
  }
}

variable "alb_deregistration_delay" {
  description = "Seconds the ALB keeps an existing connection to a draining task alive after it stops routing new requests to it. Must exceed the longest realistic SSE answer: a 30s drain would cut live streams on every scale-in or rolling deploy."
  type        = number
  default     = 300

  validation {
    condition     = var.alb_deregistration_delay >= 0 && var.alb_deregistration_delay <= 3600
    error_message = "alb_deregistration_delay must be between 0 and 3600 seconds."
  }
}

variable "certificate_arn" {
  description = "ACM certificate ARN for the optional HTTPS listener. Empty means HTTP-only (no listener on 443); the certificate is created out of band."
  type        = string
  default     = ""

  validation {
    condition     = var.certificate_arn == "" || can(regex("^arn:aws[a-z-]*:acm:", var.certificate_arn))
    error_message = "certificate_arn must be empty or an ACM certificate ARN."
  }
}

# --- Observability ---------------------------------------------------------

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the app log group."
  type        = number
  default     = 14

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.log_retention_days
    )
    error_message = "log_retention_days must be a retention value supported by CloudWatch Logs."
  }
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic for alarm notifications. Empty keeps the alarms but attaches no action, so nothing is paged."
  type        = string
  default     = ""

  validation {
    condition     = var.alarm_sns_topic_arn == "" || can(regex("^arn:aws[a-z-]*:sns:", var.alarm_sns_topic_arn))
    error_message = "alarm_sns_topic_arn must be empty or an SNS topic ARN."
  }
}

variable "alb_5xx_alarm_threshold" {
  description = "ELB-generated 5xx responses in a 5-minute period that trip the alarm."
  type        = number
  default     = 5
}

variable "unhealthy_host_alarm_threshold" {
  description = "Unhealthy targets that trip the alarm (1 catches a single-instance deployment going dark)."
  type        = number
  default     = 1
}

variable "git_sha" {
  description = "Commit SHA injected as GIT_SHA so structured logs and /health/metrics are attributable to a build. Empty is allowed (the app falls back to 'dev')."
  type        = string
  default     = ""
}
