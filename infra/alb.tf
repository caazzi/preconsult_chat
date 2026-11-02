resource "aws_lb" "this" {
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  # SSE: an answer can pause between tokens, so the connection must survive a
  # longer idle gap than the 60s default.
  idle_timeout = var.alb_idle_timeout

  tags = { Name = "${local.name}-alb" }
}

resource "aws_lb_target_group" "this" {
  name        = "${local.name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.this.id
  target_type = "ip"

  # The ALB stops sending new requests as soon as a task starts draining, but
  # it keeps existing connections until this delay elapses. It must exceed the
  # longest realistic SSE answer, otherwise a scale-in or rolling deploy cuts
  # live streams mid-response.
  deregistration_delay = var.alb_deregistration_delay

  # /health/live, not /health/ready: readiness probes Redis, and gunicorn binds
  # the port before the ASGI app is imported. A live check keeps a slow-booting
  # task out of the pool without letting a transient Redis outage recycle it.
  health_check {
    enabled             = true
    path                = "/health/live"
    port                = "traffic-port"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  # Deliberately no `stickiness` block: Redis is the session store. Sticky
  # sessions would mask a broken store and pin users to one task.

  tags = { Name = "${local.name}-tg" }
}

# HTTP-only when no certificate is set; otherwise port 80 redirects to 443.
resource "aws_lb_listener" "http" {
  count = var.certificate_arn == "" ? 1 : 0

  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  count = var.certificate_arn == "" ? 0 : 1

  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.certificate_arn == "" ? 0 : 1

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
}
