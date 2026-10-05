# Lectify CDK

BudgetStack + NetworkStack + DataStack + ComputeStack. Region default ap-southeast-2.

## 1. Prerequisites
node/npx, aws CLI v2, uv, make. Run `make install` to create a Python 3.12 venv.
Why 3.12: the system Python is 3.14 and jsii support for 3.14 is unconfirmed.

## 2. AWS access
Preferred: `aws configure sso --profile lectify`.
Else: IAM user keys in `~/.aws/credentials` under profile `lectify`.
Then: `aws configure set region ap-southeast-2 --profile lectify` and `export AWS_PROFILE=lectify`.
Never put keys, account ids or emails in the repo.

## 3. Preflight
`make preflight` checks aws CLI, caller identity, region, CDK CLI, venv Python, and runs `cdk bootstrap`.
Each line is PASS or FAIL; exit is nonzero on any failure. Exit 2 means IAM denied
creating bootstrap roles: follow the PITFALLS #14 fallback (`.planning/research/PITFALLS.md` section 14).

## 4. Manual account-type check
Billing and Cost Management console > Free Tier / Account plan. Record Free (credit-based,
accounts created from 15 Jul 2025) vs Paid plan, and the credit balance. The Free plan may
restrict services needed in Phases 14/15; upgrading keeps remaining credits.

## 5. Budget
`BUDGET_EMAIL` is required. `BUDGET_LIMIT_USD` defaults to 50 (set it to your credit pool).
Alerts by email: ACTUAL 50/80/100% and FORECASTED 100%. Credits are excluded so gross spend alerts.
Budgets data refreshes up to about once per 24h, and FORECASTED needs usage history.

## 6. Deploy / destroy
- `make deploy BUDGET_EMAIL=you@example.com` deploys all stacks (BudgetStack first).
- `make destroy` removes everything except BudgetStack.
- `make destroy-all` also removes BudgetStack.
- `make orphans` lists leftover Project=lectify VPC/NAT/EIP (fails if any). Expected leftover stacks: BudgetStack and CDKToolkit only.

## 7. DataStack
S3 buckets, RDS PostgreSQL 16.3 (db.t4g.micro, isolated subnets, TLS enforced, secret `lectify/rds/credentials`), SQS queues and an SNS topic.
Required context (or env): `app_origin` / `APP_ORIGIN` (no wildcards), `ready_emails` / `READY_EMAILS` (comma-separated). Makefile defaults: `APP_ORIGIN=http://localhost:3000`, `READY_EMAILS=demo@example.com`.
`make deploy BUDGET_EMAIL=you@example.com READY_EMAILS=op@example.com`; `make destroy` removes DataStack and NetworkStack, keeps BudgetStack.

### S3 key layout
`classes/{class_id}/lectures/{lecture_id}/{kind}/{filename}` (kind e.g. audio, transcript, materials).

### SNS limitation (v1)
The ready topic emails operator addresses only (`ready_emails`); each recipient must click the AWS subscription confirmation email. Per-student notifications are deferred to v2.

### Secrets
`make put-secrets` (or `bash scripts/put-secrets.sh`) writes SSM SecureString params `/lectify/JWT_SECRET`, `/lectify/GROQ_API_KEY`, `/lectify/GEMINI_API_KEY`.
Values come from env vars or a silent prompt, are never printed; existing params are only replaced with `--overwrite`. Never commit secrets.

## 8. Tests
`make test` and `make synth` run offline, no AWS credentials needed.

---

## 9. Phase 15 — Compute Tier & Delivery

The compute tier provisions an internet-facing Application Load Balancer (ALB), AutoScalingGroups for Web (Next.js standalone + FastAPI monolith) and Worker (background processing pipeline) tiers, systemd services, and S3-asset-based automated EC2 instance bootstrapping on Amazon Linux 2023.

### Prerequisites
Before synthesizing or deploying the compute tier, two build artifacts must exist:
1. **Next.js Standalone Bundle**:
   ```bash
   make build-web
   ```
   Runs off-instance in `frontend/`, packaging the production Next.js standalone server into `infra/cdk/build/web/`.
2. **Vendored ffmpeg Static Archive**:
   ```bash
   make vendor-ffmpeg
   ```
   Downloads the pinned AMD64 static ffmpeg build to `infra/cdk/bootstrap/vendor/`, computes its SHA-256 hash, and pins it in `infra/cdk/bootstrap/ffmpeg.sha256`.

`make deploy` runs both prerequisites automatically.

### Two-step deploy
Because the public ALB DNS name is assigned dynamically during the initial CloudFormation deployment of `ComputeStack`, S3 presigned URL CORS origins on `DataStack` require a two-step deployment:
1. **Step 1: Initial deployment with placeholder origin**:
   ```bash
   make deploy BUDGET_EMAIL=you@example.com READY_EMAILS=you@example.com
   ```
2. **Step 2: Read the ALB DNS Name from stack outputs**:
   Note the `ComputeStack.AlbDnsName` output value (e.g. `Alb-123456789.ap-southeast-2.elb.amazonaws.com`).
3. **Step 3: Redeploy with ALB DNS origin**:
   ```bash
   make deploy BUDGET_EMAIL=you@example.com READY_EMAILS=you@example.com APP_ORIGIN=http://<AlbDnsName>
   ```
   This updates the S3 bucket's CORS configuration to allow direct browser uploads from the ALB domain.

### Bootstrap DB & Seed Demo via Session Manager
The RDS PostgreSQL instance is deployed in isolated private subnets with no public access. To bootstrap tables or seed demo records, use AWS Systems Manager (SSM) Session Manager to execute the helper scripts from an EC2 instance:

1. **Find an active instance**:
   ```bash
   aws ec2 describe-instances \
     --filters "Name=tag:Project,Values=lectify" "Name=instance-state-name,Values=running" \
     --query "Reservations[].Instances[][InstanceId,Tags[?Key=='Name'].Value|[0]]" \
     --output table
   ```
2. **Start an SSM Session**:
   ```bash
   aws ssm start-session --target <instance-id>
   ```
3. **Bootstrap the Database Schema**:
   Inside the instance shell, run:
   ```bash
   sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.bootstrap_db'
   ```
   This applies database schema creation under an advisory lock (`5504283845945100081`).
4. **Seed Demo Hierarchy and Accounts**:
   Inside the instance shell, supply passwords interactively or via environment variables:
   ```bash
   sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; \
     export DEMO_ADMIN_PASSWORD=<admin-pw> \
            DEMO_TEACHER_PASSWORD=<teacher-pw> \
            DEMO_STUDENT_PASSWORD=<student-pw>; \
     cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.seed_demo'
   ```
   Never commit passwords to version control or shell history.

### Live Verification Checklist
Once deployed:
1. **ALB Root & Routing**:
   - Access `http://<AlbDnsName>/`: loads the Next.js landing page.
   - Access `http://<AlbDnsName>/healthz`: returns HTTP 200 from the frontend health check.
   - Access `http://<AlbDnsName>/api/healthz`: returns HTTP 200 `{"status":"ok"}` from FastAPI.
2. **Target Group Health**:
   - Verify both `WebTg` (:3000) and `ApiTg` (:8000) show instances as `healthy` in AWS EC2 Console.
3. **Authentication & Endpoints**:
   - Log in using a seeded demo account via the web UI.
4. **Session Manager Access & SSH Lockdown**:
   - Connect via `aws ssm start-session --target <instance-id>`.
   - Confirm SSH (port 22) is closed: port 22 is not open on security groups and instances have no EC2 key pair.
5. **Systemd Services**:
   - On the web instance: `systemctl status lectify-api lectify-web` (both active and running).
   - On the worker instance: `systemctl status lectify-worker` (active and running).

### Limitations & Architecture Notes
- **HTTP Only (Phase 15)**: The ALB listener runs on HTTP port 80. Custom domains and ACM HTTPS termination are planned for a subsequent release.
- **Connection Budget**:
  - `db.t4g.micro` RDS instance supports up to ~112 connections.
  - SQLAlchemy connection pool is configured with `pool_size=5, max_overflow=2` (7 per process).
  - Web instances (1 process) + Worker instances (max 3 instances, 1 process each) consume at most:
    `7 × (1 + 3) = 28` connections, well within the 112 limit.
- **In-Memory Rate Limiting**: SlowAPI rate limiting operates per-instance in Phase 15. Shared Redis-backed rate limiting is deferred to future multi-AZ production scale.
- **Public Subnet Instances**: Web and worker instances reside in public subnets with public IPs to allow direct outbound egress to S3 and public package repositories without incurring NAT Gateway costs ($32+/month). Inbound traffic is strictly restricted to ALB security group forwarding (:3000, :8000) with all other inbound ports blocked.

## 10. Phase 16 — Redrive the DLQ

After `maxReceiveCount=5`, poison messages land in the shared `lectify-dlq`
(14-day retention) and the lecture/job rows are marked `dead_letter`.
Redrive is operator-run, never automatic.

### Prerequisites
- Operator IAM needs `sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes` on the
  DLQ ARN plus `sqs:SendMessage` on the destination stage queue.
  The worker role lacks DLQ read access by design.
- The browser upload POST needs S3 CORS `app_origin` set to the ALB DNS.
  This is the same two-step `APP_ORIGIN` deploy from §9: first deploy with a
  placeholder, read the ALB DNS, then redeploy with
  `APP_ORIGIN=http://<AlbDnsName>` so the presigned browser POST is allowed.

### Redrive
```bash
bash scripts/redrive-dlq.sh --source lectify-dlq --dest lectify-transcribe
bash scripts/redrive-dlq.sh --source <dlq-arn> --dest <stage-queue-arn> --max 50 --force
```

### Lecture reset
Moving the message does not reset the lecture row. For each affected lecture,
as an admin:
```bash
curl -X POST "$API/api/lectures/{lecture_id}/retry" -H "Authorization: Bearer $ADMIN_JWT"
```
(`POST /lectures/{id}/retry` is admin-only; non-`dead_letter` rows get 409.)

### Confirm recovery
- DLQ depth is zero:
  `aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names ApproximateNumberOfMessages`
- The lecture left `dead_letter` (`GET /api/lectures/{id}` shows `queued`).
- A fresh `transcribe` job row exists for the lecture.
