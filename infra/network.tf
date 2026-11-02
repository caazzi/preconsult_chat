# Two public subnets, no NAT gateway.
#
# NAT gateways cost more than the compute they serve, so tasks run in public
# subnets with a public IP and a restrictive security group. Egress is needed
# for Bedrock and for the public TLS Redis (Upstash); nothing accepts inbound
# traffic except the ALB.

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  # Two AZs: the minimum for an ALB, which requires at least two subnets.
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name}-vpc" }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${local.name}-public-${local.azs[count.index]}" }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = { Name = "${local.name}-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# --- Security groups -------------------------------------------------------

resource "aws_security_group" "alb" {
  name_prefix = "${local.name}-alb-"
  description = "ALB: public HTTP/HTTPS in, container port out to the tasks only"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${local.name}-alb" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_public" {
  for_each = toset(["80", "443"])

  security_group_id = aws_security_group.alb.id
  description       = "Public HTTP(S)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
}

resource "aws_vpc_security_group_egress_rule" "alb_to_tasks" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward to the app container"
  referenced_security_group_id = aws_security_group.tasks.id
  ip_protocol                  = "tcp"
  from_port                    = var.container_port
  to_port                      = var.container_port
}

resource "aws_security_group" "tasks" {
  name_prefix = "${local.name}-task-"
  description = "ECS tasks: accept traffic from the ALB only; egress for Bedrock and Redis"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${local.name}-task" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "tasks_from_alb" {
  security_group_id            = aws_security_group.tasks.id
  description                  = "App port, from the ALB security group only"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.container_port
  to_port                      = var.container_port
}

# Public egress is required: there is no NAT gateway and no VPC endpoint for
# either Bedrock or the external TLS Redis. The task has a public IP, so this
# is the only outbound path.
resource "aws_vpc_security_group_egress_rule" "tasks_all" {
  security_group_id = aws_security_group.tasks.id
  description       = "Bedrock, Redis (public TLS) and DNS"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
