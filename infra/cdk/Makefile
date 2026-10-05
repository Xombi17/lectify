CDK := npx --no-install cdk
PY := .venv/bin/python
BUDGET_EMAIL ?=
BUDGET_LIMIT_USD ?=
REGION ?=

OPT := $(if $(BUDGET_LIMIT_USD),-c budget_limit_usd=$(BUDGET_LIMIT_USD)) $(if $(REGION),-c region=$(REGION))
CTX := -c budget_email=$(BUDGET_EMAIL) $(OPT)
PLACEHOLDER := -c budget_email=$(or $(BUDGET_EMAIL),test@example.com) $(OPT)

.PHONY: install test synth deploy destroy destroy-all preflight orphans

install:
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -r requirements-dev.txt
	npm ci

test:
	$(PY) -m pytest -q

synth:
	$(CDK) synth $(PLACEHOLDER) -q

deploy:
	@test -n "$(BUDGET_EMAIL)" || { echo "BUDGET_EMAIL is required (make deploy BUDGET_EMAIL=you@example.com)"; exit 1; }
	$(CDK) deploy --all --require-approval never $(CTX)

destroy:
	@STACKS=$$($(CDK) list $(PLACEHOLDER) | grep -v '^BudgetStack$$'); \
	if [ -z "$$STACKS" ]; then echo "nothing to destroy"; else $(CDK) destroy $$STACKS --force $(PLACEHOLDER); fi

destroy-all:
	$(CDK) destroy --all --force $(PLACEHOLDER)

preflight:
	bash scripts/preflight.sh

orphans:
	@F="--filter Name=tag:Project,Values=lectify"; \
	V=$$(aws ec2 describe-vpcs $$F --query 'Vpcs[].VpcId' --output text); \
	N=$$(aws ec2 describe-nat-gateways $$F Name=state,Values=pending,available --query 'NatGateways[].NatGatewayId' --output text); \
	E=$$(aws ec2 describe-addresses $$F --query 'Addresses[].AllocationId' --output text); \
	echo "VPCs: $$V"; echo "NAT gateways: $$N"; echo "EIPs: $$E"; \
	echo "Stacks (expected: BudgetStack, CDKToolkit only):"; \
	aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE DELETE_FAILED --query 'StackSummaries[].StackName' --output text; \
	if [ -n "$$V$$N$$E" ]; then echo "ORPHANS FOUND"; exit 1; fi; echo "no orphans"
