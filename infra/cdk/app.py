import os
import re
import sys

import aws_cdk as cdk

from lectify_cdk.budget_stack import BudgetStack
from lectify_cdk.data_stack import DataStack
from lectify_cdk.network_stack import NetworkStack

app = cdk.App()

email = app.node.try_get_context("budget_email") or os.environ.get("BUDGET_EMAIL")
if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email)):
    sys.exit("budget_email missing or invalid: pass -c budget_email=you@example.com or export BUDGET_EMAIL")

try:
    limit = float(app.node.try_get_context("budget_limit_usd") or 50)
    if limit <= 0:
        raise ValueError
except ValueError:
    sys.exit("budget_limit_usd must be a positive number (default 50)")

app_origin = str(app.node.try_get_context("app_origin") or os.environ.get("APP_ORIGIN") or "")
if not app_origin.startswith("http") or "*" in app_origin:
    sys.exit("app_origin missing or invalid (no wildcards): pass -c app_origin=http://localhost:3000 or export APP_ORIGIN")

ready_emails = [e.strip() for e in str(app.node.try_get_context("ready_emails") or os.environ.get("READY_EMAILS") or "").split(",") if e.strip()]
if not ready_emails or not all(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e) for e in ready_emails):
    sys.exit("ready_emails missing or invalid: pass -c ready_emails=operator@example.com (comma-separated) or export READY_EMAILS")

try:
    expiry = int(app.node.try_get_context("recording_expiry_days") or 30)
    if expiry <= 0:
        raise ValueError
except ValueError:
    sys.exit("recording_expiry_days must be a positive integer (default 30)")

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION") or "ap-southeast-2",
)

budget = BudgetStack(app, "BudgetStack", email=email, limit_usd=limit, env=env)
net = NetworkStack(app, "NetworkStack", env=env)
net.add_dependency(budget)
data = DataStack(app, "DataStack", network=net, app_origin=app_origin, ready_emails=ready_emails, recording_expiry_days=expiry, env=env)
data.add_dependency(net)
data.add_dependency(budget)

cdk.Tags.of(app).add("Project", "lectify")

app.synth()
