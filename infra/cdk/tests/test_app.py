import json
import os
import subprocess
import sys
from pathlib import Path

CDK_DIR = Path(__file__).resolve().parent.parent
EMAIL = "ops@example.com"
DATA = {"app_origin": "http://localhost:3000", "ready_emails": "ops@example.com"}


def _run(tmp_path, ctx, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ("BUDGET_EMAIL", "CDK_DEFAULT_ACCOUNT", "CDK_DEFAULT_REGION")}
    env["CDK_OUTDIR"] = str(tmp_path)
    env["CDK_CONTEXT_JSON"] = json.dumps({**({} if ctx.get("_nodata") else DATA), **{k: v for k, v in ctx.items() if k != "_nodata"}})
    env.update(extra_env or {})
    return subprocess.run([sys.executable, "app.py"], cwd=CDK_DIR, env=env, capture_output=True, text=True)


def _manifest(tmp_path):
    return json.loads((tmp_path / "manifest.json").read_text())["artifacts"]["BudgetStack"]


def _amount(tmp_path):
    t = json.loads((tmp_path / "BudgetStack.template.json").read_text())
    return next(r for r in t["Resources"].values() if r["Type"] == "AWS::Budgets::Budget")["Properties"]["Budget"]["BudgetLimit"]["Amount"]


def test_data_context_failfast(tmp_path):
    for bad in ({"app_origin": "*"}, {"app_origin": "http://x*"}, {"ready_emails": ""}, {"ready_emails": "nope"}):
        r = _run(tmp_path, {"budget_email": EMAIL, **bad})
        assert r.returncode != 0 and ("app_origin" in r.stderr or "ready_emails" in r.stderr)


def test_data_stack_wired(tmp_path):
    r = _run(tmp_path, {"budget_email": EMAIL})
    assert r.returncode == 0, r.stderr
    deps = json.loads((tmp_path / "manifest.json").read_text())["artifacts"]["DataStack"]["dependencies"]
    assert "NetworkStack" in deps and "BudgetStack" in deps


def test_missing_email(tmp_path):
    r = _run(tmp_path, {})
    assert r.returncode != 0 and "budget_email" in r.stderr


def test_invalid_email(tmp_path):
    r = _run(tmp_path, {"budget_email": "not-an-email"})
    assert r.returncode != 0 and "budget_email" in r.stderr


def test_env_fallback(tmp_path):
    assert _run(tmp_path, {}, {"BUDGET_EMAIL": EMAIL}).returncode == 0


def test_bad_limit(tmp_path):
    for bad in ("0", "abc"):
        r = _run(tmp_path, {"budget_email": EMAIL, "budget_limit_usd": bad})
        assert r.returncode != 0 and "budget_limit_usd" in r.stderr


def test_defaults_and_tag(tmp_path):
    r = _run(tmp_path, {"budget_email": EMAIL})
    assert r.returncode == 0, r.stderr
    m = _manifest(tmp_path)
    assert m["environment"] == "aws://unknown-account/ap-southeast-2"
    assert m["properties"]["tags"]["Project"] == "lectify"
    assert _amount(tmp_path) == 50


def test_region_and_limit_override(tmp_path):
    r = _run(tmp_path, {"budget_email": EMAIL, "region": "us-east-1", "budget_limit_usd": "75"})
    assert r.returncode == 0, r.stderr
    assert _manifest(tmp_path)["environment"].endswith("/us-east-1")
    assert _amount(tmp_path) == 75


def test_network_stack_wired(tmp_path):
    r = _run(tmp_path, {"budget_email": EMAIL})
    assert r.returncode == 0, r.stderr
    arts = json.loads((tmp_path / "manifest.json").read_text())["artifacts"]
    assert "BudgetStack" in arts["NetworkStack"]["dependencies"]
    assert "NetworkStack" not in arts["BudgetStack"].get("dependencies", [])
    assert arts["NetworkStack"]["environment"] == arts["BudgetStack"]["environment"]
    t = json.loads((tmp_path / "NetworkStack.template.json").read_text())
    vpc = next(x for x in t["Resources"].values() if x["Type"] == "AWS::EC2::VPC")
    assert {"Key": "Project", "Value": "lectify"} in vpc["Properties"]["Tags"]
