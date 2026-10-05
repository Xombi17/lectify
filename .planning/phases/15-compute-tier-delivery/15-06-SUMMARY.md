---
phase: 15-compute-tier-delivery
plan: 06
subsystem: infra
tags: [cdk, makefile, vendor-ffmpeg, readme, runbook, secrets-hygiene, status]

requires:
  - phase: 15-02
    provides: "RDS schema bootstrap script and deterministic demo seeder"
  - phase: 15-05
    provides: "Compute tier ASGs, launch templates, bootstrap scripts, and systemd units"
provides:
  - "Makefile targets for build-web, vendor-ffmpeg, deploy, bootstrap-db, and seed-demo"
  - "scripts/vendor-ffmpeg.sh with SHA-256 hash pinning"
  - "Comprehensive Phase 15 operator deployment runbook in infra/cdk/README.md"
  - "Extended secrets hygiene test covering bootstrap scripts, systemd units, and compute stacks"
  - "Updated CLAUDE.md status section per AGENTS.md rule 6"
affects: [compute-tier-delivery, phase-16]

actuals:
  tokens: 2200
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Off-instance artifact build recipes before cloud synthesis"
    - "Trust-On-First-Use (TOFU) pinned static binary vendoring with sha256sum validation"
    - "Interactive non-committing session manager runbook workflows"

key-files:
  created:
    - infra/cdk/scripts/vendor-ffmpeg.sh
  modified:
    - infra/cdk/Makefile
    - infra/cdk/README.md
    - infra/cdk/tests/test_secrets_hygiene.py
    - CLAUDE.md

key-decisions:
  - "Piped build-web and vendor-ffmpeg as mandatory deploy prerequisites in Makefile while keeping synth/destroy placeholder-safe with LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1"
  - "Vendored ffmpeg using johnvansickle release-amd64-static build with sha256 checksum pinning in bootstrap/ffmpeg.sha256"
  - "Strictly eliminated all literal passwords in README runbooks to pass secrets hygiene scanning"
  - "Detailed two-step deployment process to update S3 CORS origins with dynamically generated ALB DNS names"

requirements-completed: [COMP-04, DATA-03, SEC-03]

coverage:
  - id: D1
    description: "Makefile targets for building web, vendoring ffmpeg, and guided deploy"
    requirement: COMP-04
    verification:
      - kind: automated
        ref: "infra/cdk/Makefile"
        status: pass
    human_judgment: false
  - id: D2
    description: "Vendor ffmpeg script with SHA-256 hash generation and syntax check"
    requirement: COMP-04
    verification:
      - kind: automated
        ref: "infra/cdk/scripts/vendor-ffmpeg.sh"
        status: pass
    human_judgment: false
  - id: D3
    description: "Secrets hygiene scanner covering compute tier and bootstrap files"
    requirement: SEC-03
    verification:
      - kind: unit
        ref: "infra/cdk/tests/test_secrets_hygiene.py#test_no_secrets_in_repo_or_synth"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 15 deploy and verification runbook in README.md"
    requirement: DATA-03
    verification:
      - kind: manual
        ref: "infra/cdk/README.md"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-05
status: complete
---

# Phase 15 Plan 06: Delivery Glue & Operator Runbook Summary

**Delivery automation via Makefile targets, static ffmpeg vendoring script with SHA-256 checksum pinning, Phase 15 operator deployment runbook, secrets hygiene scanning extension, and CLAUDE.md status update.**

## Performance
- **Tasks:** 3
- **Files created:** 1
- **Files modified:** 4
- **Test suite:** 49 passed in CDK suite, 193 passed (3 skipped) in backend suite, 6 passed in frontend suite

## Accomplishments
- Created `infra/cdk/scripts/vendor-ffmpeg.sh` downloading the pinned AMD64 static ffmpeg build and writing `infra/cdk/bootstrap/ffmpeg.sha256` for instance-side verification.
- Updated `infra/cdk/Makefile` with `.PHONY` targets for `build-web`, `vendor-ffmpeg`, `bootstrap-db`, `seed-demo`, and chained `deploy: build-web vendor-ffmpeg`, while adding `LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1` to `synth`, `destroy`, and `destroy-all`.
- Extended `infra/cdk/tests/test_secrets_hygiene.py` to explicitly verify scanning of all bootstrap scripts, systemd units, compute stack definitions, and vendor scripts with zero secrets found.
- Updated `infra/cdk/README.md` with full operator documentation covering two-step deployment (ALB DNS → S3 CORS update), database bootstrap & demo seeding via AWS SSM Session Manager, the live verification checklist, and system connection budgeting.
- Updated `CLAUDE.md` `## Status` per AGENTS.md rule 6 with comprehensive Phase 15 accomplishments, verified test counts, and bumped the next queue card to Phase 16.

## Deviations from Plan
- Sanitized password command examples in `infra/cdk/README.md` to use `<placeholder>` tokens rather than quoted mock passwords, satisfying strict regex checks in `test_secrets_hygiene.py`.
