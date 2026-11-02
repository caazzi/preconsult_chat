output "function_url" {
  description = "Public Lambda function URL (RESPONSE_STREAM, AuthType NONE)."
  value       = aws_lambda_function_url.app.function_url
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain (use it until the custom domain resolves)."
  value       = aws_cloudfront_distribution.app.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution id, for cache invalidation and smoke tests."
  value       = aws_cloudfront_distribution.app.id
}

output "ecr_repository_url" {
  description = "ECR repository to push the Lambda image to."
  value       = aws_ecr_repository.app.repository_url
}

output "log_group_name" {
  description = "CloudWatch log group for the application function."
  value       = aws_cloudwatch_log_group.app.name
}

output "function_name" {
  description = "Lambda function name."
  value       = aws_lambda_function.app.function_name
}

output "live_alias_arn" {
  description = "ARN of the stable `live` alias the function URL serves. CI moves this for deploy and rollback."
  value       = aws_lambda_alias.live.arn
}

output "live_alias_name" {
  description = "Alias name used by the function URL and CI deploy/rollback commands."
  value       = aws_lambda_alias.live.name
}

output "warmer_function_name" {
  description = "Warmer Lambda function name, or null when the warmer is disabled."
  value       = var.enable_warmer ? aws_lambda_function.warmer[0].function_name : null
}
