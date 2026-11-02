resource "aws_ecs_cluster" "this" {
  name = local.name
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = local.container_name
      image     = var.image
      essential = true

      portMappings = [{
        containerPort = var.container_port
        hostPort      = var.container_port
        protocol      = "tcp"
      }]

      # Same values the Cloud Run deploy passes today, plus GIT_SHA so the
      # PHI-free structured events and /health/metrics are attributable to a
      # build. TRUST_PROXY_HEADERS is load-bearing: the ALB appends the real
      # client to X-Forwarded-For and get_client_ip() reads the last hop.
      environment = [
        { name = "PORT", value = tostring(var.container_port) },
        { name = "LLM_PROVIDER", value = var.llm_provider },
        { name = "LLM_MODEL", value = var.llm_model },
        { name = "LLM_REGION", value = var.llm_region },
        { name = "TRUST_PROXY_HEADERS", value = "true" },
        { name = "ALLOW_PUBLIC_INIT", value = "true" },
        { name = "WEB_DIST_DIR", value = "/app/web/dist" },
        { name = "GIT_SHA", value = var.git_sha },
      ]

      # Names are env-var names; values come from SSM at task start. The
      # configuration never reads or stores the secret values.
      secrets = [
        for name, arn in local.parameter_arns : { name = name, valueFrom = arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "app"
          "awslogs-create-group"  = "false"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "this" {
  name                              = local.name
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.this.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"
  health_check_grace_period_seconds = var.health_check_grace_period_seconds

  network_configuration {
    # Public subnets + public IP: there is no NAT gateway. Inbound is still
    # restricted to the ALB by the task security group.
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = true
  }

  # No stickiness on the target group on purpose: sessions live in Redis (see
  # alb.tf), so any task can serve any request.
  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = local.container_name
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # Autoscaling owns the count after the first deployment; without this every
  # apply would reset it to var.desired_count.
  lifecycle {
    ignore_changes = [desired_count]
  }

  # A task starts as soon as the service is created, so the secret-read and
  # log/ECR policies must exist first, not merely be planned in parallel.
  depends_on = [
    aws_iam_role_policy.execution_secrets,
    aws_iam_role_policy_attachment.execution_managed,
    aws_lb_listener.http,
    aws_lb_listener.http_redirect,
    aws_lb_listener.https,
  ]
}

resource "aws_appautoscaling_target" "ecs" {
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.this.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.min_capacity
  max_capacity       = var.max_capacity
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${local.name}-cpu-target-tracking"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value = var.cpu_target_utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
