data "archive_file" "warmer" {
  type        = "zip"
  source_file = "${path.module}/warmer/pinger.py"
  output_path = "${path.module}/.terraform/preconsult-warmer.zip"
}

resource "aws_cloudwatch_log_group" "warmer" {
  name              = "/aws/lambda/${local.warmer_function_name}"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "warmer_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "warmer" {
  name               = "${local.warmer_function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.warmer_assume_role.json
}

data "aws_iam_policy_document" "warmer" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.warmer.arn}:*"]
  }
}

resource "aws_iam_role_policy" "warmer" {
  name   = "write-warmer-logs"
  role   = aws_iam_role.warmer.id
  policy = data.aws_iam_policy_document.warmer.json
}

# The pinger needs no Lambda permissions: it only makes an outbound HTTPS GET
# to the public function URL. Its role is logs-only.
resource "aws_lambda_function" "warmer" {
  function_name    = local.warmer_function_name
  role             = aws_iam_role.warmer.arn
  runtime          = "python3.12"
  handler          = "pinger.handler"
  filename         = data.archive_file.warmer.output_path
  source_code_hash = data.archive_file.warmer.output_base64sha256
  architectures    = ["x86_64"]
  memory_size      = 128
  timeout          = 30

  environment {
    variables = {
      TARGET_URL = aws_lambda_function_url.app.function_url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.warmer,
    aws_iam_role_policy.warmer,
  ]
}

resource "aws_cloudwatch_event_rule" "warmer" {
  name                = "${local.name}-warmer"
  description         = "Keep one PreConsult Lambda execution environment warm."
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "warmer" {
  rule      = aws_cloudwatch_event_rule.warmer.name
  target_id = "warmer"
  arn       = aws_lambda_function.warmer.arn
}

resource "aws_lambda_permission" "warmer_events" {
  statement_id  = "AllowEventBridgeInvokeWarmer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.warmer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.warmer.arn
}
