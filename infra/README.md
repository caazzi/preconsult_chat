# PreConsult on AWS Lambda

Reference Terraform for a **lowest-fixed-cost** deployment of the existing
PreConsult container. It replaces the closed ECS/Fargate design with:

```
CloudFront (optional custom domain, ACM in us-east-1)
  └── Lambda Function URL (InvokeMode = RESPONSE_STREAM, AuthType = NONE)
        └── container image + AWS Lambda Web Adapter → gunicorn, unchanged
              └── Upstash Redis over public TLS (NO VPC)
```

There is **no ALB, no VPC, no NAT gateway and no always-on compute**. The app
still runs in the same image; the Lambda Web Adapter starts the existing
gunicorn `CMD` and proxies function-URL requests to it on `:8080`.

> **Agents never apply.** This directory is code and documentation only. An
> agent must not run `terraform apply`/`plan` against a real account, `aws`
> commands, or any deploy. A human with the account/state credentials applies.

## What is fixed vs per-request

| Component | Fixed monthly cost | Notes |
| --- | --- | --- |
| Lambda | $0 idle | Billed per request + GB-second; scales to zero. |
| Function URL | $0 | No charge for the endpoint itself. |
| CloudFront | $0 | Per request/GB only, no commitment. |
| ECR | ~$0.10/GB-month | Lifecycle keeps the last 10 images. |
| CloudWatch Logs | Retention-bound | 30 days by default; ingestion charged. |
| Alarms | $0 (first 10) | Two alarms; optional SNS actions. |
| Warmer | ~$0.05/month | Opt-in (`enable_warmer`, default `false`): one 128 MB ping every 5 minutes. |
| ALB / NAT / Fargate | **not provisioned** | Those were the fixed-cost drivers. |

CloudFront has no fixed fee, so it is optional in cost terms but included here
for TLS and an optional custom domain. The default behavior is deliberately
uncached (`CachingDisabled`), so it does not reduce Lambda invocations for the
SPA assets.

## What lives outside Terraform

Terraform never creates or reads secret values, and it does not own DNS or the
certificate:

1. **Remote state** — an S3 bucket (versioned, encrypted, public access
   blocked) and, for Terraform 1.9.x, a DynamoDB table with a `LockID` string
   partition key. Both are created once, out of band.
2. **SSM SecureString parameters** — `PRECONSULT_API_KEY`, `REDIS_URL` and
   `SESSION_SECRET`. Create them with `aws ssm put-parameter --type
   SecureString` (human step). This stack receives their **names** and builds
   ARNs; Lambda resolves the values with the execution role. `REDIS_URL`
   should be the Upstash TLS URL (`rediss://...`).
3. **Bedrock model access** — enable the Anthropic Claude Haiku model and the
   `us.` cross-region inference profile in the target account/region. Without
   model access, invocations fail with AccessDenied even though IAM is correct.
4. **ACM certificate (custom domain only)** — must be in **us-east-1**,
   DNS-validated, in the same account as CloudFront.
5. **DNS** — at Cloudflare, point the hostname at the CloudFront distribution
   domain as **DNS-only (grey cloud)**. Proxying Cloudflare in front of
   CloudFront adds a second CDN and a second client-IP hop; do not do it
   without a new header/rate-limit design. Apex records need Cloudflare's
   CNAME flattening.
6. **The image** — the ECR repository is `IMMUTABLE`, so the first apply needs
   an image tag that already exists (see bootstrap order).

## Bootstrap order (human)

Terraform cannot create a Lambda image function before its image exists. Use a
targeted apply for the repository only, push an image, then apply everything:

```bash
cd infra
export PATH="/tmp/opencode/tools:$PATH"   # pinned Terraform 1.9.8

# 1. State backend (partial config; nothing account-specific is committed).
terraform init \
  -backend-config="bucket=<state-bucket>" \
  -backend-config="key=preconsult/lambda/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="encrypt=true" \
  -backend-config="dynamodb_table=<lock-table>"

# 2. Repository only (still an apply; human-only).
terraform apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app

# 3. Build and push an amd64 image with Bedrock installed (see next section).
# 4. Apply the rest, pinned to that tag.
terraform apply -var-file=prod.tfvars -var="image_tag=<git-sha>"
```

The full apply publishes version 1 and points the `live` alias at it; the
function URL is qualified by that alias from the start. Later deploys publish
new versions and move the alias (see below). The image tag must exist before
this step because Lambda validates the image when creating the function.

For local syntax checks no backend or credentials are needed:

```bash
export PATH="/tmp/opencode/tools:$PATH"
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate
```

## Building the image

The default image is unchanged: `UV_EXTRAS` is empty, so it still ships Vertex
only. The Lambda image installs the Bedrock extra and targets `linux/amd64`
(the function is `x86_64`):

```bash
AWS_REGION=us-east-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO=$(terraform -chdir=infra output -raw ecr_repository_url)
TAG=$(git rev-parse --short HEAD)

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
      "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker buildx build \
  --platform linux/amd64 \
  --build-arg UV_EXTRAS="--extra bedrock" \
  -t "${REPO}:${TAG}" \
  --push .
```

The Dockerfile also copies the AWS Lambda Web Adapter (`0.9.1`) into
`/opt/extensions/lambda-adapter`. It is inert outside Lambda, so the Cloud Run
image is unaffected. The `CMD` is untouched; the adapter launches it and waits
for `GET /health/live` before forwarding traffic (`AWS_LWA_READINESS_CHECK_PATH`).

## Deploying, aliases and rollback

The ECR repository is immutable, so every deploy uses a new tag (normally the
git SHA). Terraform bootstraps the function once; after that, **CI owns code
deploys**, and the function URL is pinned to the `live` alias, never to
`$LATEST`. A deploy publishes a new version and moves the alias:

```bash
VERSION=$(aws lambda update-function-code \
  --function-name preconsult-prod \
  --image-uri "$REPO:$TAG" \
  --publish \
  --query Version --output text)

aws lambda update-alias \
  --function-name preconsult-prod \
  --name live \
  --function-version "$VERSION"
```

Rolling back is the reverse, with no rebuild and no URL change:

```bash
aws lambda update-alias \
  --function-name preconsult-prod \
  --name live \
  --function-version <previous-version>
```

Terraform deliberately ignores `image_uri` on the function and
`function_version` on the alias. Without those ignores, any later apply would
revert a CI deploy/rollback to the bootstrap version. Consequently `image_tag`
is a **bootstrap-only** value: changing it after the first apply does not
deploy anything.

Keep `GIT_SHA` in the function configuration in step with the deployed image
(it tags structured log events). Lambda environment variables are
version-specific, so update the value before publishing a version, or the new
version inherits the old tag. Also keep the rollback depth inside the ECR
lifecycle window (ten images): a new sandbox pulls its image, so the rollback
target must still exist in ECR.

## CloudFront details

The distribution is a pass-through, not a cache:

- viewer protocol: `redirect-to-https`
- `compress = false` (compression buffers streams and is not wanted here)
- cache policy: **CachingDisabled** (`4135ea2d-6df8-44a3-bd57-4b1e2ff0ed06`)
- origin request policy: **AllViewerExceptHostHeader**
  (`b689b0a8-53d0-40ab-baf2-68738e2966ac`)
- origin read timeout: 60 seconds (the CloudFront maximum)

The original brief named **AllViewer** (`216adef6-5c7f-47e4-b989-5492eafa07d3`).
AWS documents that forwarding the viewer `Host` header to a Lambda function
URL origin "can prevent them from working": the function URL expects its own
domain, and even the default `*.cloudfront.net` host differs from
`*.lambda-url.*`. `AllViewerExceptHostHeader` still forwards every other
header, all cookies and all query strings, which is what the HttpOnly session
cookie and SSE require; CloudFront rewrites `Host` to the origin domain. The
managed ids are pinned above rather than looked up, so the policies stay
verifiable without an AWS call.

`domain_name` and `acm_certificate_arn` are both-or-neither. When both are
empty CloudFront uses its `*.cloudfront.net` certificate and domain; when set,
the certificate must be in us-east-1 and DNS must point at CloudFront.

## Streaming caveat (read before cutover)

Function URLs created with `invoke_mode = "RESPONSE_STREAM"` stream SSE, but
CloudFront is an HTTP proxy with a **60-second cap on the gap between response
packets**. It is not a cap on total stream duration, but it is a hard edge:

- the app's first-token budget is 30 s (`LLM_TTFT_TIMEOUT_S`), fine;
- its inter-token idle budget is 60 s (`LLM_IDLE_TIMEOUT_S`), exactly at the
  CloudFront limit, so a model pause near the budget can produce a 504;
- `compress = false` and `CachingDisabled` avoid the common buffering causes,
  but CloudFront may still buffer the first bytes of a response at some edges;
- CloudFront speaks HTTP/1.1 to custom origins, not HTTP/2.

This is **unproven without an account**. Validate a real Q&A stream through
CloudFront (not only the function URL) before calling the stack production
ready. If streaming through CloudFront is unacceptable, the fallback is to
serve the SPA through CloudFront and keep the API on the function URL (which
needs a same-origin/CORS and cookie design), or to put the whole app on the
function URL and give up the custom domain. Do not silently lower the app's
idle timeout just to fit CloudFront; that changes answer quality/latency.

## Cold starts and concurrency

- Lambda scales to zero. A cold start includes image pull (the app image is
  large), adapter boot, gunicorn start and Python/Starlette imports. Expect
  multi-second latency after idle; no number here is measured.
- Each sandbox handles **one request at a time**. Every concurrent SSE stream
  needs its own sandbox, and each can cold start independently.
- Provisioned concurrency is the only guarantee and is deliberately not used:
  it is always-on compute, the cost model this stack is avoiding.
- `timeout = 120` bounds a single stream. Long streams are cut at 120 s even
  without CloudFront.
- Upstash is reached over public TLS; there is no VPC/NAT. Many sandboxes mean
  many Redis connections, so watch the Upstash connection/quota limits.

### Warmer is opt-in

`enable_warmer` defaults to `false`. When it is false Terraform creates **no**
EventBridge rule, pinger Lambda, zip archive or warmer IAM role. Enable it only
after measuring how often a real user actually waits on a cold start; a
five-minute ping is otherwise speculative spend. When enabled it costs roughly
**$0.05/month** and keeps at most one sandbox warm — it does not pre-warm
concurrency, and every additional concurrent visitor can still cold start.

## Auth, client IP and privacy

`AuthType = "NONE"` is intentional and equivalent to Cloud Run's
`--allow-unauthenticated`: the app is already publicly reachable and enforces
`PRECONSULT_API_KEY`, the HttpOnly session cookie, the bot gate, per-IP rate
limits and the daily session quota. CloudFront is a CDN, **not** an auth
boundary; the function URL remains publicly reachable and can be called
directly. Adding WAF or IAM auth here would be a new layer, not a replacement
for the app's controls.

`TRUST_PROXY_HEADERS=true` is kept. The app trusts the **rightmost**
`X-Forwarded-For` hop because Cloud Run appends the real client there. Through
CloudFront + a function URL, the hop order must be re-measured with a
header-echo probe before production: CloudFront adds the viewer address, the
function URL front end may add another hop, and the Lambda Web Adapter proxies
from localhost (so `request.client.host` is not a usable fallback either). If
the rightmost entry is not the viewer, every visitor shares one
rate-limit/quota bucket. This is a launch blocker, not a detail;
`TRUST_CF_CONNECTING_IP` stays false because CloudFront does not set
`cf-connecting-ip`.

CloudWatch receives only the app's existing metadata events (no complaint,
answers, conditions or medications). CloudFront access logging is **not**
enabled: access logs contain request paths and query strings, and the
zero-PHI posture is easier to keep by not collecting them. The log group has
retention and no subscription.

## State, drift and ownership

- State: S3 with encryption and versioning; DynamoDB locking on Terraform 1.9.
  If the toolchain moves to Terraform 1.10+, `use_lockfile = true` can replace
  the DynamoDB table; do not change it in the same commit as a deploy.
- CloudFront changes take time to deploy (`wait_for_deployment` defaults true).
- Code/version ownership: Terraform creates the first published version and
  the `live` alias, then ignores `image_uri` and the alias's
  `function_version`. CI publishes versions and moves the alias; an apply
  cannot silently undo a deploy or a rollback. The function URL is qualified
  by `live` from creation, so this is not a later migration. If Terraform
  itself changes version-specific configuration (environment variables), that
  publishes a new version; move `live` to it explicitly, because Terraform
  will not.
- ECR is immutable and keeps ten images. A new sandbox pulls its image, so a
  rollback target must still exist in ECR; a rollback older than those ten
  images requires a rebuild.
- The function role is least-privilege: its own log stream, its one ECR
  repository, the named SSM parameters (plus KMS decrypt through SSM), and the
  Claude inference profile plus the wildcard-region foundation model ARN that
  cross-region inference needs.
- Alarms are `AWS/Lambda` `Errors` and `Throttles`, five-minute sums. Set
  `alarm_sns_topic_arn` to notify; without it they are visible but silent.

## Files

```
infra/
  versions.tf            Terraform/provider pins, partial S3 backend
  variables.tf           names, sizes, model ids, SSM parameter names
  main.tf                ECR, log group, Lambda, live alias, function URL, permissions
  iam.tf                 execution role (logs, ECR, Bedrock, SSM/KMS)
  cloudfront.tf          distribution + managed policy ids
  observability.tf       Errors/Throttles alarms
  warmer.tf              opt-in EventBridge rule + pinger Lambda
  warmer/pinger.py       tiny stdlib health pinger
  outputs.tf             URL, alias ARN, CloudFront domain, ECR URL, log group
  prod.tfvars.example    non-secret example values
```
