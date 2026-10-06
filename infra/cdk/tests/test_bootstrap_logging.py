"""Static checks: CloudWatch agent configs, unit log paths, bootstrap wiring."""
import json
import subprocess
from pathlib import Path

from lectify_cdk.compute_iam import LOG_GROUP_API, LOG_GROUP_WEB, LOG_GROUP_WORKER

B = Path(__file__).resolve().parents[1] / "bootstrap"


def _map(name):
    raw = (B / name).read_text()
    assert "retention_in_days" not in raw
    lst = json.loads(raw)["logs"]["logs_collected"]["files"]["collect_list"]
    assert all(e["log_stream_name"] == "{instance_id}" for e in lst)
    return {e["file_path"]: e["log_group_name"] for e in lst}


def test_agent_configs():
    assert _map("cloudwatch-agent-web.json") == {
        "/var/log/lectify/api.log": LOG_GROUP_API,
        "/var/log/lectify/web.log": LOG_GROUP_WEB,
    }
    assert _map("cloudwatch-agent-worker.json") == {
        "/var/log/lectify/worker.log": LOG_GROUP_WORKER
    }


def test_units_log_to_files():
    for svc in ("api", "web", "worker"):
        u = (B / "systemd" / f"lectify-{svc}.service").read_text()
        path = f"/var/log/lectify/{svc}.log"
        assert f"StandardOutput=append:{path}" in u
        assert f"StandardError=append:{path}" in u
        if svc != "web":
            assert "Environment=PYTHONUNBUFFERED=1" in u


def test_bootstrap_wiring():
    c = (B / "common.sh").read_text()
    for needle in ("amazon-cloudwatch-agent-ctl", "copytruncate",
                   "setup_log_files()", "install_cloudwatch_agent()"):
        assert needle in c
    for sh, tier in (("api.sh", "web"), ("worker.sh", "worker")):
        s = (B / sh).read_text()
        assert f"install_cloudwatch_agent {tier}" in s
        assert 0 <= s.index("setup_log_files") < s.index("systemctl enable")
        assert s.index("install_cloudwatch_agent") < s.index("systemctl enable")


def test_bash_syntax():
    for sh in ("common.sh", "api.sh", "worker.sh"):
        subprocess.run(["bash", "-n", str(B / sh)], check=True)
