data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${local.name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "app" {
  # The log group is created by Terraform with retention, so the role needs
  # only stream writes, not CreateLogGroup.
  statement {
    sid = "WriteOwnLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.app.arn}:*"]
  }

  # Image-based Lambda pulls the image with the execution role.
  statement {
    sid = "PullImage"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  statement {
    sid = "InvokeClaude"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream",
    ]
    resources = [
      local.bedrock_inference_profile_arn,
      local.bedrock_foundation_model_arn,
    ]
  }

  # Lambda resolves the SSM SecureString environment values with this role.
  # Only the three named parameters are readable; values never enter state.
  statement {
    sid = "ReadNamedSecrets"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = values(local.ssm_parameter_arns)
  }

  statement {
    sid       = "DecryptSsmSecureStrings"
    actions   = ["kms:Decrypt"]
    resources = ["arn:${local.partition}:kms:${var.aws_region}:${local.account_id}:key/*"]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["ssm.${var.aws_region}.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "preconsult-lambda"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}
