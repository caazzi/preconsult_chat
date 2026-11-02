resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.log_retention_days
  # Default (unset) KMS key: log contents are already PHI-free by contract
  # (see core/observability.py), so no customer-managed key is required.
}
