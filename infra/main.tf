data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  name                 = "${var.name_prefix}-${var.environment}"
  function_name        = local.name
  warmer_function_name = "${local.name}-warmer"
  log_group_name       = "/aws/lambda/${local.function_name}"

  account_id = data.aws_caller_identity.current.account_id
  partition  = data.aws_partition.current.partition

  tags = merge(
    {
      Project     = "preconsult"
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags,
  )

  # ARNs, never values. Lambda resolves SecureString parameters referenced by
  # ARN at create/update and on cold start using the execution role.
  ssm_parameter_arns = {
    for key, name in var.ssm_secret_names :
    key => "arn:${local.partition}:ssm:${var.aws_region}:${local.account_id}:parameter${name}"
  }

  bedrock_inference_profile_arn = "arn:${local.partition}:bedrock:${var.llm_region}:${local.account_id}:inference-profile/${var.bedrock_inference_profile_id}"
  # Cross-region inference can route to any us-* region, so the foundation
  # model ARN deliberately wildcards the region.
  bedrock_foundation_model_arn = "arn:${local.partition}:bedrock:*::foundation-model/${var.bedrock_foundation_model_id}"

  function_environment = {
    LLM_PROVIDER                 = "bedrock"
    LLM_MODEL                    = var.bedrock_inference_profile_id
    LLM_REGION                   = var.llm_region
    TRUST_PROXY_HEADERS          = "true"
    ALLOW_PUBLIC_INIT            = "true"
    WEB_DIST_DIR                 = "/app/web/dist"
    AWS_LWA_PORT                 = "8080"
    AWS_LWA_READINESS_CHECK_PATH = "/health/live"
    AWS_LWA_INVOKE_MODE          = "response_stream"

    # Structured log events tag themselves with GIT_SHA/K_REVISION. Lambda sets
    # neither, so without this every event would say revision=dev. CI updates
    # this alongside the image when it deploys out of band.
    GIT_SHA = var.image_tag

    # Secret *names* are resolved by Lambda; no plaintext secret is in state.
    PRECONSULT_API_KEY = local.ssm_parameter_arns.api_key
    REDIS_URL          = local.ssm_parameter_arns.redis_url
    SESSION_SECRET     = local.ssm_parameter_arns.session_secret
  }

  alarm_actions = var.alarm_sns_topic_arn == "" ? [] : [var.alarm_sns_topic_arn]
}

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the ten most recent images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "app" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "app" {
  function_name = local.function_name
  role          = aws_iam_role.app.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"

  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  environment {
    variables = local.function_environment
  }

  # The log group must exist first so Lambda does not create an unretained one.
  depends_on = [
    aws_cloudwatch_log_group.app,
    aws_iam_role_policy.app,
  ]
}

# AuthType NONE is deliberate: the app is already publicly reachable (Cloud
# Run's --allow-unauthenticated) and enforces its own API key / bot gate /
# per-IP limits / session quota. CloudFront is a CDN, not an auth layer.
resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"
}

# Function URLs require both actions (see AWS "Invoking Lambda function URLs").
resource "aws_lambda_permission" "function_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.app.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "function_url_invoke" {
  statement_id             = "AllowPublicFunctionInvokeViaUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.app.function_name
  principal                = "*"
  invoked_via_function_url = true
}
