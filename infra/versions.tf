terraform {
  required_version = ">= 1.6.0"

  # Partial configuration on purpose: the bucket, key, region and lock table
  # are environment/account facts, not source. Supply them at init time (see
  # README.md) so no account id or bucket name is committed.
  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
