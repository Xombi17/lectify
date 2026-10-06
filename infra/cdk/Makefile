CDK := npx --no-install cdk
PY := .venv/bin/python
BUDGET_EMAIL ?=
BUDGET_LIMIT_USD ?=
REGION ?=
APP_ORIGIN ?= http://localhost:3000
READY_EMAILS ?= demo@example.com

OPT := $(if $(BUDGET_LIMIT_USD),-c budget_limit_usd=$(BUDGET_LIMIT_USD)) $(if $(REGION),-c region=$(REGION))
APP := -c app_origin=$(APP_ORIGIN) -c ready_emails=$(READY_EMAILS)
CTX := -c budget_email=$(BUDGET_EMAIL) $(APP) $(OPT)
PLACEHOLDER := -c budget_email=$(or $(BUDGET_EMAIL),test@example.com) $(APP) $(OPT)

.PHONY: aws-pause aws-resume aws-status put-secrets install test synth deploy destroy destroy-all preflight orphans build-web vendor-ffmpeg bootstrap-db seed-demo

install:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -r requirements-dev.txt
	npm ci

test:
	$(PY) -m pytest -q

build-web:
	bash scripts/build-web.sh

vendor-ffmpeg:
	bash scripts/vendor-ffmpeg.sh

synth:
	LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1 $(CDK) synth $(PLACEHOLDER) -q

deploy: build-web vendor-ffmpeg
	@test -n "$(BUDGET_EMAIL)" || { echo "BUDGET_EMAIL is required (make deploy BUDGET_EMAIL=you@example.com)"; exit 1; }
	$(CDK) deploy --all --require-approval never $(CTX)

destroy:
	@STACKS=$$(LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1 $(CDK) list $(PLACEHOLDER) | grep -v '^BudgetStack$$'); \
	if [ -z "$$STACKS" ]; then echo "nothing to destroy"; else LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1 $(CDK) destroy $$STACKS --force $(PLACEHOLDER); fi

destroy-all:
	LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1 $(CDK) destroy --all --force $(PLACEHOLDER)

put-secrets:
	bash scripts/put-secrets.sh

preflight:
	bash scripts/preflight.sh

bootstrap-db:
	@echo "To bootstrap the RDS database schema, start an SSM session on an API or worker instance:"
	@echo "  aws ssm start-session --target <instance-id>"
	@echo "Once logged in, run:"
	@echo "  sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.bootstrap_db'"

seed-demo:
	@echo "To seed demo users and sample hierarchy, start an SSM session on an API or worker instance:"
	@echo "  aws ssm start-session --target <instance-id>"
	@echo "Once logged in, run (specify DEMO_*_PASSWORD in the environment):"
	@echo "  sudo -u lectify bash -c 'set -a; source /etc/lectify/app.env; set +a; export DEMO_ADMIN_PASSWORD=... DEMO_TEACHER_PASSWORD=... DEMO_STUDENT_PASSWORD=...; cd /opt/lectify/backend && /opt/lectify/venv/bin/python -m scripts.seed_demo'"

orphans:
	@F="--filter Name=tag:Project,Values=lectify"; \
	V=$$(aws ec2 describe-vpcs $$F --query 'Vpcs[].VpcId' --output text); \
	N=$$(aws ec2 describe-nat-gateways $$F Name=state,Values=pending,available --query 'NatGateways[].NatGatewayId' --output text); \
	E=$$(aws ec2 describe-addresses $$F --query 'Addresses[].AllocationId' --output text); \
	echo "VPCs: $$V"; echo "NAT gateways: $$N"; echo "EIPs: $$E"; \
	echo "Stacks (expected: BudgetStack, CDKToolkit only):"; \
	aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE DELETE_FAILED --query 'StackSummaries[].StackName' --output text; \
	if [ -n "$$V$$N$$E" ]; then echo "ORPHANS FOUND"; exit 1; fi; echo "no orphans"

aws-pause:
	bash scripts/aws-pause.sh pause

aws-resume:
	bash scripts/aws-pause.sh resume

aws-status:
	bash scripts/aws-pause.sh status
