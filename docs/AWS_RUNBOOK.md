# Lectify AWS Runbook

Operator guide: fresh clone to a deployed, seeded, verified stack, and back to zero. Commands run from `infra/cdk` unless stated. Detail lives in [infra/cdk/README.md](../infra/cdk/README.md); this file is the ordered path through it. Placeholders such as `<AlbDnsName>` and `<instance-id>` are never real values; do not paste account ids, hostnames or secrets into the repo.

## 0. Quick reference

| Task | Command |
|---|---|
| Create CDK venv | `make install` |
| Check account/region/CDK | `make preflight` |
| Deploy everything | `make deploy BUDGET_EMAIL=you@example.com READY_EMAILS=you@example.com` |
| Store secrets | `make put-secrets` |
| Bootstrap schema | `make bootstrap-db` (prints SSM commands) |
| Seed demo users | `make seed-demo` (prints SSM commands) |
| Redrive DLQ | `bash scripts/redrive-dlq.sh --source lectify-dlq --dest lectify-transcribe` |
| Scale-out demo | `bash scripts/scale-demo.sh stub-on` / `run` / `stub-off` |
| Pause / resume / status | `make aws-pause` / `make aws-resume` / `make aws-status` |
| Teardown | `make destroy` (keeps BudgetStack), `make destroy-all` |
| Leftover check | `make orphans` |

## 1. Prerequisites and preflight

Needs node/npx, aws CLI v2, uv, make, and a profile named `lectify` (`export AWS_PROFILE=lectify`). See README sections 1-2.

```bash
make install
make preflight
```

Before deploying, confirm the selected Region in AWS Settings (default `ap-southeast-2`) and check spend-limit status in AWS Settings > Billing. A spend limit that trips pauses the project and surfaces as sudden AccessDenied errors.

## 2. Budget and ops topic

`BudgetStack` holds the budget (default $50, `BUDGET_LIMIT_USD`) and the `lectify-ops` SNS topic. It persists across `make destroy`. After the first deploy, click the confirmation link in the subscription emails (budget address and `READY_EMAILS` recipients); verify with `aws sns list-subscriptions-by-topic --topic-arn <arn>` (no `PendingConfirmation`). Details: README sections 5 and 11.

## 3. Build and deploy

```bash
make deploy BUDGET_EMAIL=you@example.com READY_EMAILS=you@example.com
```

`make deploy` builds the Next.js bundle (`make build-web`) and vendors ffmpeg (`make vendor-ffmpeg`) first. Read `ComputeStack.AlbDnsName` from the outputs, then redeploy once with `APP_ORIGIN=http://<AlbDnsName>` so S3 CORS allows browser uploads (README section 9, two-step deploy). `LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1` is only for destroy or placeholder synth, never for a real deploy.

## 4. Secrets

```bash
make put-secrets            # JWT_SECRET, GROQ_API_KEY, GEMINI_API_KEY -> /lectify/* SecureString
bash scripts/put-secrets.sh --overwrite   # replace existing values
```

Values come from env vars or a silent prompt and are never printed. Never commit them or type them inline in shell history. Restart services (or let ASG instances refresh) after changing a value.

## 5. Schema bootstrap and seed

RDS is private; run the helpers on an instance through Session Manager (README section 9).

```bash
aws ec2 describe-instances --filters "Name=tag:Project,Values=lectify" "Name=instance-state-name,Values=running" \
  --query "Reservations[].Instances[][InstanceId,Tags[?Key=='Name'].Value|[0]]" --output table
aws ssm start-session --target <instance-id>
```

Inside the session:

```bash
sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.bootstrap_db'
sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; export DEMO_ADMIN_PASSWORD=... DEMO_TEACHER_PASSWORD=... DEMO_STUDENT_PASSWORD=...; cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.seed_demo'
```

Both are idempotent. Instances run Python 3.11; the CDK venv is 3.12; local dev is 3.14.

## 6. Verify

```bash
curl -i http://<AlbDnsName>/healthz        # web
curl -i http://<AlbDnsName>/api/healthz    # api
```

Then log in with a seeded account and run the live upload-to-ready checklist (VER-01) and DLQ proof (VER-02) in [SPEC_UPLOAD.md](SPEC_UPLOAD.md). README section 9 has the target group and systemd checks.

## 7. Operate

- Alarms (7 ops + 2 scaling) email the `lectify-ops` topic: backlog age/depth, DLQ depth, worker/web CPU, dead-letter jobs, API 5xx. See README section 11.
- Logs: `aws logs tail /lectify/worker --follow` (also `/lectify/api`, `/lectify/web`; 7-day retention).
- Dashboard: CloudWatch > Dashboards > `lectify-overview`.
- Worker scaling: ASG min 1, max 3. Scale out when backlog (transcribe + materials, visible + in-flight) >= 5 (+1) or >= 20 (+2); scale in after 15 minutes at <= 1.
- Admin can reset a `dead_letter` lecture with `POST /api/lectures/{id}/retry`.

## 8. DLQ redrive

```bash
bash scripts/redrive-dlq.sh --source lectify-dlq --dest lectify-transcribe
```

Use either the message move or `/retry` per lecture, never both. Full procedure and recovery checks: README section 10. Confirm DLQ depth returns to zero.

## 9. Scale-out demo (VER-03)

Uses a provider stub (no paid API calls). The stub is only honoured when ENV is aws/demo/staging.

```bash
bash scripts/scale-demo.sh stub-on
TEACHER_PASSWORD=... bash scripts/scale-demo.sh run
bash scripts/scale-demo.sh stub-off
```

Expected timeline: roughly 30-45 minutes (about 2 min alarm, about 5 min EC2 boot and warmup, 15 min scale-in window). The script logs TRANSITION lines and writes the full log to `cdk.out/scale-demo-<timestamp>.log`. Always run `stub-off` afterwards; never leave the stub on. Finish with `make aws-pause` or `make destroy`.

## 10. Load test (VER-04)

1. Install k6 from the official Grafana k6 documentation.
2. Seed load users on an instance (SSM session, as in section 5):
   `export LOAD_USER_PASSWORD=...` then `... /opt/lectify/venv/bin/python -m scripts.load_users seed --count 200`.
3. On the laptop, mint tokens (needs `JWT_SECRET`, run from `backend/`):
   ```bash
   export JWT_SECRET=$(aws ssm get-parameter --name /lectify/JWT_SECRET --with-decryption --query Parameter.Value --output text)
   python -m scripts.load_users mint --count 200
   ```
4. Run `loadtest/browse.js` and `loadtest/login_storm.js` as separate k6 runs against `http://<AlbDnsName>`. Results go to the gitignored `loadtest/out/`.
5. Expect Api5xx or CPU alarm emails during the login storm; that is data, not a failure of the run.
6. Delete `loadtest/out/tokens.json` afterwards (it holds valid JWTs), then pause or destroy.
7. Record results in [CAPACITY_REPORT.md](CAPACITY_REPORT.md).

## 11. Pause and resume

```bash
make aws-pause    # ASGs to 0, stop RDS
make aws-resume   # start RDS, restore ASGs, wait for /healthz
make aws-status   # read-only
```

RDS auto-restarts after 7 days stopped; re-run pause if away longer. `make deploy` undoes a pause.

## 12. Teardown

```bash
make destroy       # everything except BudgetStack
make destroy-all   # also BudgetStack (ops topic CMK enters a 7-day deletion window; re-confirm email after redeploy)
make orphans       # fails if VPC/NAT/EIP tagged Project=lectify remain
```

Expected leftovers after `destroy-all`: CDKToolkit only.

## 13. Cost notes

All figures are estimates as of 2026-10; verify in the Billing console.

- Paused: ALB plus RDS storage is about $1/day.
- No NAT gateways by design (instances use public subnets), avoiding $32+/month.
- t3.small web and worker instances plus the db.t4g.micro RDS dominate running cost.
- SQS, CloudWatch and S3 are minor at demo volume.
- Budget alerts fire at the configured default of $50 (50/80/100% actual, 100% forecast).
- Keep load-test and scale-demo windows short and finish each with pause or destroy.

## 14. Troubleshooting

- Scale-in never observed: stuck in-flight messages keep backlog above 1; check the queues and DLQ.
- Scale-out slow: new worker instances need several minutes to boot and bootstrap.
- Empty log group on first deploy: `sudo systemctl restart amazon-cloudwatch-agent` on the instance.
- Sudden AccessDenied on previously working calls: check the spend limit in AWS Settings > Billing.
- Services unreachable after days paused: RDS auto-restarted or ASGs still at 0; run `make aws-status`.
