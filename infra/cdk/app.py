import os
import re
import sys

import aws_cdk as cdk

from lectify_cdk.budget_stack import BudgetStack
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

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION") or "ap-south-1",
)

budget = BudgetStack(app, "BudgetStack", email=email, limit_usd=limit, env=env)
net = NetworkStack(app, "NetworkStack", env=env)
net.add_dependency(budget)

cdk.Tags.of(app).add("Project", "lectify")

app.synth()
