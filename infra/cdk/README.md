# Lectify CDK (Phase 12)

BudgetStack + NetworkStack + DataStack. Region default ap-southeast-2.

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
