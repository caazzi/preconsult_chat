output "alb_dns_name" {
  description = "Public DNS name of the ALB. Point the cutover DNS record at this (or at an alias using alb_zone_id)."
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "Canonical hosted zone id for Route 53 alias records at cutover."
  value       = aws_lb.this.zone_id
}

output "ecr_repository_url" {
  description = "Repository to push CI-built images to."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  description = "ECS service name (for `aws ecs update-service --force-new-deployment`)."
  value       = aws_ecs_service.this.name
}

output "log_group_name" {
  description = "CloudWatch log group receiving the container's awslogs output."
  value       = aws_cloudwatch_log_group.app.name
}
