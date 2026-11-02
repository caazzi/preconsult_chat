data "aws_caller_identity" "current" {}

locals {
  name = "${var.project_name}-${var.environment}"

  container_name = "preconsult"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # SSM SecureString ARNs are derived from the parameter *names* only. The
  # values are created out of band (console/CLI) and are never read, written or
  # stored by this configuration.
  parameter_arns = {
    REDIS_URL          = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.redis_url_param_name}"
    PRECONSULT_API_KEY = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.preconsult_api_key_param_name}"
    SESSION_SECRET     = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.session_secret_param_name}"
  }
}
