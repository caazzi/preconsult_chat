# PreConsult on AWS — ECS Fargate (Wave 6a)

Infrastructure-only Terraform for running the existing `preconsult` container on
ECS Fargate behind an ALB. `pre-consult.org` stays on its current host; this
directory creates no DNS records and does not cut traffic over.

The app contract this stack preserves: one container (gunicorn + one uvicorn
worker), `$PORT` 8080, SSE answer streams, Redis only for sessions, and no
durable storage of request bodies.

## Layout

| File | Contents |
|---|---|
| `versions.tf` | Terraform/provider pins, partial S3 backend, provider `default_tags` |
| `locals.tf` | Name prefix, tags, SSM parameter ARNs derived from names |
| `variables.tf` | All inputs and their defaults |
| `network.tf` | VPC, 2 public subnets in 2 AZs, IGW + route table, ALB/task security groups |
| `ecr.tf` | Private repo: immutable tags, scan on push, keep last 10 images |
| `logs.tf` | CloudWatch log group with configurable retention |
| `iam.tf` | Execution role (ECR/logs/SSM) and task role (Bedrock, scoped to one model) |
| `ecs.tf` | Cluster, task definition, service, autoscaling |
| `alb.tf` | Internet-facing ALB, target group, HTTP listener + optional HTTPS |
| `alarms.tf` | ALB 5xx and unhealthy-target alarms |
| `outputs.tf` | ALB DNS/zone, ECR URL, cluster/service names, log group |
| `prod.tfvars.example` | Placeholders only — no secrets, account ids or cert ARNs |

## Remote state (S3 + DynamoDB)

The backend block is intentionally empty (`backend "s3" {}`). The bucket, key
and lock table are supplied at init time, so nothing account-specific is
committed. Create them out of band, once:

- S3 bucket: versioning on, default SSE on, all public access blocked.
- DynamoDB table: partition key `LockID` (string), on-demand billing.

Then initialise:

```bash
cd infra
terraform init \
  -backend-config="bucket=REPLACE_WITH_STATE_BUCKET" \
  -backend-config="key=preconsult/infra/prod.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=REPLACE_WITH_LOCK_TABLE" \
  -backend-config="encrypt=true"
```

The generated `.terraform.lock.hcl` is committed. It records hashes for
`linux_amd64` only (what CI and this machine use); on macOS/ARM run
`terraform providers lock -platform=linux_amd64 -platform=darwin_arm64` and
commit the result rather than letting `init` rewrite it.

## Validation (no cloud access needed)

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

`init -backend=false` still downloads the pinned AWS provider; if that download
fails, validation could not be run at all — do not report it as passing.

## Apply policy

**Agents never run `terraform apply`, `terraform plan` against a real account,
or any `aws` command.** This repository's deploy policy is that changes reach
production only through a human-reviewed path. A human runs:

```bash
terraform init ...                       # as above
terraform plan  -var-file=prod.tfvars     # inspect
terraform apply -var-file=prod.tfvars     # human only
```

## Out of band (not created by this configuration)

| Item | Why |
|---|---|
| SSM SecureString values for `/preconsult/prod/REDIS_URL`, `/preconsult/prod/PRECONSULT_API_KEY`, `/preconsult/prod/SESSION_SECRET` | Terraform only references the parameter *names*; values must never enter HCL, tfvars or state. Create them in the console or with `aws ssm put-parameter --type SecureString`. |
| ACM certificate (optional) | `certificate_arn` is empty by default; set it to enable the HTTPS listener. The certificate must be in `var.aws_region` (ALB requirement) and validated before use. |
| DNS for `pre-consult.org` | Wave 6a creates no DNS. At cutover, point the record at `alb_dns_name` (alias using `alb_zone_id`). |
| SNS topic | `alarm_sns_topic_arn` empty means alarms exist with no action. |
| State bucket + DynamoDB table | See Remote state above. |
| The container image | Must be built with the `bedrock` extra (`uv sync --locked --extra bedrock`). The default Dockerfile installs Vertex only, so the stock image raises `LLM_PROVIDER=bedrock requires the 'bedrock' extra` on the first question. Wave 6a is infra only and does not change the Dockerfile. |
| Route 53 / registrar | Not managed here; the domain is currently served elsewhere. |

## Design notes

- **No NAT gateway.** Two public subnets across two AZs carry the ALB and the
  tasks. Tasks get a public IP for Bedrock/Redis egress; the task security
  group accepts inbound only from the ALB security group on the container port.
- **Health check is `GET /health/live`**, matcher `200`, not `/health/ready`:
  readiness probes Redis, and gunicorn binds the port before the ASGI app is
  imported. The live probe is dependency-free.
- **`idle_timeout = 300`** on the ALB because SSE answers can pause between
  tokens. `alb_deregistration_delay` defaults to 300s as well: the ALB stops
  new requests on a draining task immediately but keeps existing connections
  until the delay elapses, and the drain must outlast the longest answer
  stream. Lowering it to seconds would cut live answers on every scale-in or
  rolling deploy.
- **No target-group stickiness.** Redis is the session store of record;
  stickiness would mask a broken store instead of failing loudly.
- **Immutable ECR tags + lifecycle of 10 images.** Deploy a fresh tag per
  commit; a rollback needs its old tag to still exist.
- **Bedrock IAM is scoped to one inference profile plus the underlying model
  ARN.** Cross-region profiles (`us.…`) fan out to the foundation model in
  other regions, hence `arn:aws:bedrock:*::foundation-model/…`. The policy also
  allows `bedrock:Converse`/`ConverseStream` because `ChatBedrockConverse` uses
  the Converse API, not `InvokeModel`, in the normal streaming path.
- **Secrets are resolved by the execution role from SSM at task start** and
  injected as container `secrets`, never as plaintext environment values.
- **`GIT_SHA`** is injected as an env var (empty by default) so the app's
  revision tag is not permanently `"dev"` on ECS. Set it per deploy.
- Task definition: 512 CPU / 1024 MiB (0.5 vCPU, the same shape as the current
  cost-optimised Cloud Run profile), one warm task (min 1), autoscaling to 5 at
  60% CPU.
- **Alarms with an empty `alarm_sns_topic_arn`** are created but have no
  actions: they appear in the console and can be wired to a topic later, but
  they notify nobody. `HTTPCode_ELB_5XX_Count` covers ALB-generated 5xx
  (e.g. no healthy target); application 5xx are `HTTPCode_Target_5XX_Count`
  and are not alarmed here.
- **Client IP:** the ALB appends the real client to `X-Forwarded-For`, matching
  the Cloud Run behaviour the app was measured against, so
  `TRUST_PROXY_HEADERS=true` keeps the per-IP rate limits and 20/day session
  quota meaningful. `TRUST_CF_CONNECTING_IP` stays unset/false (the domain is
  not proxied through Cloudflare).

## Assumptions to revisit

- **Region:** `aws_region` and `llm_region` both default to `us-east-1`, and the
  default `llm_model` is the `us.` cross-region inference profile. Another
  geography needs the matching profile id (`eu.…`/`apac.…`) and usually a
  different `llm_region`; the IAM inference-profile ARN follows `llm_region`.
- **Edge:** HTTP-only unless `certificate_arn` is set; then port 80 redirects
  to 443 and the ALB serves the cert directly. HTTP-only is for first-boot
  validation, not real use: the app's session cookie is `Secure` by default, so
  browsers will not send it over plain HTTP and the wizard cannot create a
  session. Set `certificate_arn` before any user traffic. Behind Cloudflare's
  proxy later, set `TRUST_CF_CONNECTING_IP=true` in the container env and
  re-check the client-IP policy.
- **State:** moving off S3+DynamoDB (e.g. Terraform Cloud) means replacing the
  empty `backend "s3" {}` block and re-running `init -migrate-state`.
- Platform version `LATEST` and x86_64 are assumed; an ARM build needs
  `cpu_architecture = "ARM64"` and a matching image.
