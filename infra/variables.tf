variable "aws_region" {
  description = "Region for the Lambda function, ECR repository, SSM parameters and CloudWatch resources."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Lowercase prefix for every resource name."
  type        = string
  default     = "preconsult"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.name_prefix))
    error_message = "name_prefix must be 2-31 lowercase letters, digits or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment, appended to resource names."
  type        = string
  default     = "prod"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,15}$", var.environment))
    error_message = "environment must be 2-16 lowercase letters, digits or hyphens and start with a letter."
  }
}

variable "image_tag" {
  description = "ECR tag used for the initial Lambda image. The repository is IMMUTABLE, so use a git SHA (not 'latest'). Terraform only bootstraps the function; later code deploys are CI's job."
  type        = string
  default     = "bootstrap"

  validation {
    condition     = can(regex("^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid ECR tag."
  }
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB. 1024 keeps the container image + gunicorn viable; SSE holds one sandbox per stream."
  type        = number
  default     = 1024

  validation {
    condition     = var.lambda_memory_mb >= 128 && var.lambda_memory_mb <= 10240
    error_message = "lambda_memory_mb must be between 128 and 10240."
  }
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds. CloudFront's per-packet origin timeout is 60s, so a single SSE gap must stay below that."
  type        = number
  default     = 120

  validation {
    condition     = var.lambda_timeout_seconds >= 1 && var.lambda_timeout_seconds <= 900
    error_message = "lambda_timeout_seconds must be between 1 and 900."
  }
}

variable "llm_region" {
  description = "Bedrock region (LLM_REGION). Must be a region where the chosen Claude model/profile is available."
  type        = string
  default     = "us-east-1"
}

variable "bedrock_inference_profile_id" {
  description = "Cross-region inference profile id, used as LLM_MODEL and as the inference-profile IAM scope."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "bedrock_foundation_model_id" {
  description = "Foundation model id under the inference profile. The model may be served from any us-* region, hence the wildcard region in its ARN."
  type        = string
  default     = "anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "ssm_secret_names" {
  description = "SSM SecureString parameter NAMES (not values). The Lambda execution role can read only these, and the function receives their ARNs so Lambda resolves the values at runtime."
  type = object({
    api_key        = string
    redis_url      = string
    session_secret = string
  })
  default = {
    api_key        = "/preconsult/prod/PRECONSULT_API_KEY"
    redis_url      = "/preconsult/prod/REDIS_URL"
    session_secret = "/preconsult/prod/SESSION_SECRET"
  }

  validation {
    condition     = alltrue([for name in values(var.ssm_secret_names) : startswith(name, "/")])
    error_message = "Every SSM parameter name must start with '/'."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the function and warmer logs."
  type        = number
  default     = 30

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.log_retention_days
    )
    error_message = "log_retention_days must be a retention value supported by CloudWatch Logs."
  }
}

variable "domain_name" {
  description = "Optional custom domain for CloudFront (e.g. pre-consult.org). Empty = use the CloudFront default domain."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN for domain_name. Must live in us-east-1 (CloudFront requirement). Empty = CloudFront default certificate."
  type        = string
  default     = ""

  validation {
    condition     = var.acm_certificate_arn == "" || can(regex("^arn:aws:acm:us-east-1:", var.acm_certificate_arn))
    error_message = "acm_certificate_arn must be empty or an ACM ARN in us-east-1."
  }
}

variable "cloudfront_price_class" {
  description = "CloudFront price class. PriceClass_100 is the cheapest; it does not include South America edges."
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.cloudfront_price_class)
    error_message = "cloudfront_price_class must be PriceClass_100, PriceClass_200 or PriceClass_All."
  }
}

variable "alarm_sns_topic_arn" {
  description = "Optional SNS topic for CloudWatch alarm actions. Empty = alarms exist but notify nobody."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Extra tags applied to every taggable resource."
  type        = map(string)
  default     = {}
}
