---
phase: 15-compute-tier-delivery
plan: 05
subsystem: infra
tags: [cdk, ec2, asg, launch-template, bootstrap, systemd, imdsv2]

requires:
  - phase: 15-01
    provides: "Backend shallow /healthz, DB_AUTO_CREATE flag, and supervisor loop"
  - phase: 15-03
    provides: "Frontend /healthz and relative API client"
  - phase: 15-04
    provides: "ComputeStack ALB, target groups, and least-privilege IAM roles"
provides:
  - "Launch templates with IMDSv2 required, hop limit 1, 20GB gp3 root volume, and Session Manager access"
  - "Web ASG (min 1, max 2) attached to web & api target groups with ELB health check grace period"
  - "Worker ASG (min 1, max 3 hard-capped) with EC2 health checks"
  - "Idempotent AL2023 bootstrap scripts and hardened systemd service unit files"
  - "App.py ComputeStack integration with fail-fast artifact checks and placeholder synth fallback"
affects: [15-06, compute-tier-delivery]

actuals:
  tokens: 2800
  tasks: 4
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Hardened Launch Templates with mandatory IMDSv2 hop limit 1 and encrypted EBS"
    - "Thin user-data bootstrapping via S3 assets and systemd service supervision"
    - "Fail-fast CDK synthesis checks preventing deployment of unbuilt artifacts"

key-files:
  created:
    - infra/cdk/bootstrap/common.sh
    - infra/cdk/bootstrap/api.sh
    - infra/cdk/bootstrap/worker.sh
    - infra/cdk/bootstrap/systemd/lectify-api.service
    - infra/cdk/bootstrap/systemd/lectify-web.service
    - infra/cdk/bootstrap/systemd/lectify-worker.service
    - infra/cdk/bootstrap/ffmpeg.sha256
  modified:
    - backend/services/storage_service.py
    - infra/cdk/.gitignore
    - infra/cdk/app.py
    - infra/cdk/lectify_cdk/compute_stack.py
    - infra/cdk/tests/test_app.py
    - infra/cdk/tests/test_compute.py
    - infra/cdk/tests/test_compute_iam.py
    - infra/cdk/tests/test_secrets_hygiene.py

key-decisions:
  - "Configured IMDSv2 with HttpTokens=required and HttpPutResponseHopLimit=1 to guard against SSRF credential leakage"
  - "Enforced worker ASG maximum capacity hard-cap of 3 instances (WORKER_MAX) to control cloud spend"
  - "Created systemd service units with MemoryMax limits (API 700M, Web 600M, Worker 1200M) and graceful SIGTERM shutdown (120s timeout)"
  - "Implemented _require_artifacts in app.py with LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK escape hatch for destroy workflows"
  - "Mapped S3 bucket name in storage_service.py to accept both OBJECT_STORAGE_BUCKET and S3_BUCKET"

requirements-completed: [COMP-02, COMP-03, COMP-04, COMP-05]

coverage:
  - id: D1
    description: "Launch templates with IMDSv2 hop limit 1, gp3 encrypted EBS, and public IP"
    requirement: COMP-02
    verification:
      - kind: unit
        ref: "infra/cdk/tests/test_compute.py#test_launch_templates"
        status: pass
    human_judgment: false
  - id: D2
    description: "Web ASG min 1 max 2 with ELB health checks attached to both target groups"
    requirement: COMP-03
    verification:
      - kind: unit
        ref: "infra/cdk/tests/test_compute.py#test_web_asg"
        status: pass
    human_judgment: false
  - id: D3
    description: "Worker ASG min 1 max 3 with EC2 health check and zero load balancer attachments"
    requirement: COMP-03
    verification:
      - kind: unit
        ref: "infra/cdk/tests/test_compute.py#test_worker_asg"
        status: pass
    human_judgment: false
  - id: D4
    description: "Fail-fast CDK synth checks for missing web build or unchecksummed ffmpeg archive"
    requirement: COMP-05
    verification:
      - kind: unit
        ref: "infra/cdk/tests/test_app.py#test_failfast_missing_web"
        status: pass
      - kind: unit
        ref: "infra/cdk/tests/test_app.py#test_failfast_missing_ffmpeg"
        status: pass
      - kind: unit
        ref: "infra/cdk/tests/test_app.py#test_failfast_ffmpeg_sha256_placeholder"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-05
status: complete
---

# Phase 15 Plan 05: Compute Tier Launch Templates, ASGs, Bootstrap & Systemd Summary

**EC2 Launch Templates and AutoScalingGroups for Web and Worker tiers with IMDSv2 enforcement, S3-asset-driven bootstrap scripts, hardened systemd units, and app.py fail-fast synthesis validation.**

## Performance
- **Tasks:** 4
- **Files created:** 7
- **Files modified:** 8
- **Test suite:** 49 passed in CDK suite, 193 passed (3 skipped) in backend suite

## Accomplishments
- Implemented `common.sh`, `api.sh`, and `worker.sh` for unattended Amazon Linux 2023 instance provisioning with swap allocation, user isolation (`lectify:lectify`), python3.11 virtualenv setup, node20 installation, asset extraction, and sha256-verified ffmpeg deployment.
- Defined hardened systemd units (`lectify-api.service`, `lectify-web.service`, `lectify-worker.service`) with memory caps, working directory isolation, `SIGTERM` kill signal, and 120s timeout stop window for graceful connection/job draining.
- Configured Launch Templates in `ComputeStack` with `require_imdsv2=True`, `http_put_response_hop_limit=1`, 20GB gp3 encrypted root volumes, and no EC2 key pair (Session Manager only).
- Configured Web ASG (min 1, max 2, ELB health check grace 300s) attached to both Web (:3000) and API (:8000) target groups, and Worker ASG (min 1, max 3 hard-cap `WORKER_MAX`, EC2 health check) without ALB exposure.
- Wired `ComputeStack` into `infra/cdk/app.py` with dependencies on `NetworkStack` and `DataStack`.
- Implemented `_require_artifacts()` in `app.py` ensuring synthesis fails fast with actionable guidance when `build/web/server.js`, `bootstrap/vendor/ffmpeg...`, or `bootstrap/ffmpeg.sha256` checksums are missing, with `LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1` for destroy and placeholder operations.

## Deviations from Plan
- Updated `storage_service.py` to accept `S3_BUCKET` in addition to `OBJECT_STORAGE_BUCKET` for consistent environment naming across compute tiers and bootstrap scripts.
- Added `bootstrap/vendor/` to `infra/cdk/.gitignore` to ensure vendored binary archives are not committed to git.
