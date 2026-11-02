data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- Execution role: what the ECS agent needs to start the container --------

resource "aws_iam_role" "execution" {
  name               = "${local.name}-ecs-execution"
  description        = "ECS agent: pull the image, write logs, resolve the SSM secrets"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

# Managed policy: ECR pull (image + layers) and CloudWatch Logs write.
resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "execution_secrets" {
  statement {
    sid       = "ReadConfiguredSecureStrings"
    effect    = "Allow"
    actions   = ["ssm:GetParameter", "ssm:GetParameters"]
    resources = values(local.parameter_arns)
  }
}

# Scoped to exactly the three parameter ARNs this task definition references.
# A customer-managed KMS key on those parameters would additionally need
# kms:Decrypt here; the default alias/aws/ssm key does not.
resource "aws_iam_role_policy" "execution_secrets" {
  name   = "${local.name}-ssm-secrets"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

# --- Task role: what the app itself may call -------------------------------

resource "aws_iam_role" "task" {
  name               = "${local.name}-ecs-task"
  description        = "PreConsult app: Bedrock invoke on the configured Haiku model only"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid    = "InvokeConfiguredHaikuModel"
    effect = "Allow"

    # ChatBedrockConverse (langchain-aws) calls the Converse / ConverseStream
    # APIs; InvokeModel* covers the direct-runtime path. All four actions are
    # scoped to the same inference profile and foundation model.
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream",
    ]

    resources = [
      # The cross-region inference profile the app names in LLM_MODEL.
      "arn:aws:bedrock:${var.llm_region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.llm_model}",
      # A cross-region profile fans out to the underlying model in every
      # destination region, so the model ARN is region-wildcarded.
      "arn:aws:bedrock:*::foundation-model/${var.llm_foundation_model_id}",
    ]
  }
}

resource "aws_iam_role_policy" "task_bedrock" {
  name   = "${local.name}-bedrock-invoke"
  role   = aws_iam_role.task.id
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}
