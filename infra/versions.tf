terraform {
  required_version = ">= 1.9.0"

  # Partial configuration on purpose: bucket, key, region and lock table are
  # supplied at init time so no account id or bucket name is ever committed.
  # See "Remote state" in infra/README.md for the -backend-config flags.
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
