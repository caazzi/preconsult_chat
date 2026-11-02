# Managed policy ids, documented rather than looked up:
#
#   CachingDisabled
#     4135ea2d-6df8-44a3-bd57-4b1e2ff0ed06
#   AllViewerExceptHostHeader
#     b689b0a8-53d0-40ab-baf2-68738e2966ac
#
# AllViewer (216adef6-5c7f-47e4-b989-5492eafa07d3) is deliberately NOT used:
# AWS documents that Lambda function URL origins expect Host to be the origin
# domain, and forwarding the viewer Host "can prevent them from working". Even
# the default *.cloudfront.net viewer host differs from the *.lambda-url.*
# origin host. AllViewerExceptHostHeader still forwards every other header,
# all cookies and all query strings, which is what the HttpOnly session cookie
# and SSE need; CloudFront rewrites Host to the origin domain.
locals {
  cloudfront_caching_disabled_policy_id       = "4135ea2d-6df8-44a3-bd57-4b1e2ff0ed06"
  cloudfront_all_viewer_except_host_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  cloudfront_default_certificate              = var.acm_certificate_arn == ""
  lambda_function_url_host                    = trimsuffix(replace(aws_lambda_function_url.app.function_url, "https://", ""), "/")
  custom_domain_configured                    = var.domain_name != ""
}

resource "aws_cloudfront_distribution" "app" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "PreConsult ${var.environment} (Lambda function URL origin)"
  price_class     = var.cloudfront_price_class
  aliases         = local.custom_domain_configured ? [var.domain_name] : []

  origin {
    domain_name = local.lambda_function_url_host
    origin_id   = "lambda-function-url"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      # Maximum CloudFront allows. CloudFront measures this as the gap
      # between response packets, not total stream duration; see README.
      origin_read_timeout = 60
    }
  }

  default_cache_behavior {
    target_origin_id       = "lambda-function-url"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    # Compression and caching both break streaming and cookies. POSTs are
    # never cached with CachingDisabled; this is a pass-through CDN.
    compress                 = false
    cache_policy_id          = local.cloudfront_caching_disabled_policy_id
    origin_request_policy_id = local.cloudfront_all_viewer_except_host_policy_id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = local.cloudfront_default_certificate
    acm_certificate_arn            = local.cloudfront_default_certificate ? null : var.acm_certificate_arn
    ssl_support_method             = local.cloudfront_default_certificate ? null : "sni-only"
    minimum_protocol_version       = local.cloudfront_default_certificate ? null : "TLSv1.2_2021"
  }

  lifecycle {
    precondition {
      condition     = local.custom_domain_configured == (var.acm_certificate_arn != "")
      error_message = "domain_name and acm_certificate_arn must be set together (or both left empty)."
    }
  }
}
