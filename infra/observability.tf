locals {
  # Explicit topic wins; otherwise use the topic created from alarm_email;
  # otherwise the alarms are visible but silent.
  alarm_actions = (
    var.alarm_sns_topic_arn != ""
    ? [var.alarm_sns_topic_arn]
    : var.alarm_email != ""
    ? [aws_sns_topic.alarms[0].arn]
    : []
  )
}

resource "aws_sns_topic" "alarms" {
  count = var.alarm_email == "" ? 0 : 1
  name  = "${local.name}-alarms"
}

# Email subscriptions are created PENDING: the recipient must click the
# confirmation link before CloudWatch notifications are delivered.
resource "aws_sns_topic_subscription" "alarms_email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name}-lambda-errors"
  alarm_description   = "PreConsult Lambda reported one or more invocation errors in five minutes."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.app.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${local.name}-lambda-throttles"
  alarm_description   = "PreConsult Lambda was throttled; concurrency may be exhausted."
  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  dimensions          = { FunctionName = aws_lambda_function.app.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}

resource "aws_cloudwatch_metric_alarm" "cloudfront_5xx_rate" {
  alarm_name          = "${local.name}-cloudfront-5xx-rate"
  alarm_description   = "CloudFront is returning 5xx to more than 1% of viewers for two consecutive five-minute periods. This alarm exists because AWS/Lambda Errors only counts failed invocations: an app that returns 503 llm_unavailable (or any other 5xx) is a successful invocation and stays invisible there."
  namespace           = "AWS/CloudFront"
  metric_name         = "5xxErrorRate"
  dimensions          = { DistributionId = aws_cloudfront_distribution.app.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alarm_actions
}
