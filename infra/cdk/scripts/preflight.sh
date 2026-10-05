#!/usr/bin/env bash
# Account preflight (ACCT-01). Prints PASS/FAIL per check; exit nonzero on any failure.
set -u
cd "$(dirname "$0")/.." || exit 1
export AWS_PROFILE="${AWS_PROFILE:-lectify}"
export BUDGET_EMAIL="${BUDGET_EMAIL:-test@example.com}"
FAIL=0
pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; FAIL=$((FAIL + 1)); }

if aws --version >/dev/null 2>&1; then pass "aws cli"; else fail "aws cli"; fi

if ID=$(aws sts get-caller-identity --output json 2>&1); then
  pass "identity"; echo "$ID"
  ACCOUNT=$(echo "$ID" | python3 -c 'import sys,json;print(json.load(sys.stdin)["Account"])')
else
  fail "identity"
  echo "hint: aws sso login --profile $AWS_PROFILE"
  exit 1
fi

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null)}}"
REGION="${REGION:-ap-southeast-2}"
echo "region=$REGION"
export AWS_REGION="$REGION"

if npx --no-install cdk --version; then pass "cdk cli"; else fail "cdk cli"; fi

if .venv/bin/python -c 'import sys;assert sys.version_info[:2] in ((3,11),(3,12)),sys.version;print(sys.version.split()[0])' 2>/dev/null; then
  pass "python venv"
else
  fail "python venv (run: make install)"
fi

OUT=$(mktemp)
if npx --no-install cdk bootstrap "aws://$ACCOUNT/$REGION" 2>&1 | tee "$OUT"; [ "${PIPESTATUS[0]}" -eq 0 ]; then
  pass "bootstrap"
else
  fail "bootstrap"
  if grep -Eq 'AccessDenied|iam:CreateRole|not authorized to perform: iam' "$OUT"; then
    echo "IAM denied. Fallback (PITFALLS #14): use the sandbox-provided role via --role-arn,"
    echo "or a custom DefaultStackSynthesizer qualifier / pre-existing roles."
    echo "See .planning/research/PITFALLS.md section 14. Stopping."
    rm -f "$OUT"
    exit 2
  fi
fi
rm -f "$OUT"

echo "MANUAL: Billing console > Free Tier / Account plan: confirm Free (credit) plan vs Paid plan and remaining credits; see README"
echo "Summary: $FAIL failure(s)"
exit $FAIL
