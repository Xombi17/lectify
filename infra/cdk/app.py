import os
from pathlib import Path
import re
import sys

import aws_cdk as cdk

from lectify_cdk.budget_stack import BudgetStack
from lectify_cdk.compute_stack import ComputeStack
from lectify_cdk.data_stack import DataStack
from lectify_cdk.network_stack import NetworkStack
from lectify_cdk.observability_stack import ObservabilityStack


def _require_artifacts(cdk_dir: Path):
    backend_dir = cdk_dir.parent.parent / "backend"
    web_dir = cdk_dir / "build" / "web"
    bootstrap_dir = cdk_dir / "bootstrap"
    ffmpeg_archive = bootstrap_dir / "vendor" / "ffmpeg-release-amd64-static.tar.xz"
    sha_file = bootstrap_dir / "ffmpeg.sha256"

    if os.environ.get("LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK") == "1":
        # Create lightweight stub dirs for destroy / synth placeholder paths
        stub_dir = cdk_dir / "build" / "stub"
        stub_web = stub_dir / "web"
        stub_web.mkdir(parents=True, exist_ok=True)
        (stub_web / "server.js").write_text("// stub for cdk synth/destroy\n")

        stub_vendor = stub_dir / "vendor"
        stub_vendor.mkdir(parents=True, exist_ok=True)
        stub_ffmpeg = stub_vendor / "ffmpeg-release-amd64-static.tar.xz"
        if not stub_ffmpeg.exists():
            stub_ffmpeg.write_bytes(b"stub")

        actual_web = web_dir if (web_dir / "server.js").exists() or list(web_dir.glob("**/server.js")) else stub_web
        actual_ffmpeg = ffmpeg_archive if ffmpeg_archive.is_file() else stub_ffmpeg
        return str(backend_dir), str(actual_web), str(bootstrap_dir), str(actual_ffmpeg)

    # Strict fail-fast mode
    has_server_js = web_dir.is_dir() and ((web_dir / "server.js").exists() or any(web_dir.rglob("server.js")))
    if not has_server_js:
        sys.exit("Missing web build: build/web/server.js not found. Run 'make build-web' before synthesizing.")

    if not ffmpeg_archive.is_file():
        sys.exit("Missing ffmpeg archive: bootstrap/vendor/ffmpeg-release-amd64-static.tar.xz not found. Run 'make vendor-ffmpeg' before synthesizing.")

    if not sha_file.is_file():
        sys.exit("Missing ffmpeg checksum file: bootstrap/ffmpeg.sha256 not found. Run 'make vendor-ffmpeg' before synthesizing.")

    lines = [ln.strip() for ln in sha_file.read_text().splitlines()]
    has_hash = any(ln and not ln.startswith("#") for ln in lines)
    if not has_hash:
        sys.exit("ffmpeg.sha256 contains only placeholder comments. Run 'make vendor-ffmpeg' before synthesizing.")

    return str(backend_dir), str(web_dir), str(bootstrap_dir), str(ffmpeg_archive)


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

cdk_dir = Path(__file__).resolve().parent
backend_dir, web_dir, bootstrap_dir, ffmpeg_archive = _require_artifacts(cdk_dir)

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

compute = ComputeStack(
    app,
    "ComputeStack",
    network=net,
    data=data,
    backend_dir=backend_dir,
    web_dir=web_dir,
    bootstrap_dir=bootstrap_dir,
    ffmpeg_archive=ffmpeg_archive,
    env=env,
)
compute.add_dependency(net)
compute.add_dependency(data)

obs = ObservabilityStack(app, "ObservabilityStack", data=data, compute=compute, budget=budget, env=env)
obs.add_dependency(compute)
obs.add_dependency(budget)

cdk.Tags.of(app).add("Project", "lectify")

app.synth()
