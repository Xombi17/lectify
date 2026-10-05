import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".venv", "node_modules", ".git", "cdk.out", "__pycache__", ".pytest_cache", "vendor"}
PATTERNS = [
    r"AKIA[0-9A-Z]{16}",
    r"gsk_[A-Za-z0-9]{20,}",
    r"AIza[0-9A-Za-z_\-]{35}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)(jwt_secret|password|api_key)\s*[=:]\s*[\"'][^\"'\s]{8,}[\"']",
]


def _files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not (SKIP & set(p.relative_to(ROOT).parts)) and p.suffix not in {".pyc", ".png", ".xz", ".tar"}:
            yield p


def _synth(tmp_path):
    out = tmp_path / "out"
    code = "import runpy,sys; sys.argv=['app.py']; runpy.run_path('app.py', run_name='__main__')"
    env = {**os.environ, "CDK_OUTDIR": str(out), "CDK_DEFAULT_ACCOUNT": "123456789012", "CDK_DEFAULT_REGION": "ap-southeast-2",
           "LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK": "1",
           "CDK_CONTEXT_JSON": json.dumps({"budget_email": "a@example.com", "app_origin": "http://localhost:3000", "ready_emails": "a@example.com"})}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)
    return out


def test_no_secrets_in_repo_or_synth(tmp_path):
    out = _synth(tmp_path)
    file_list = list(_files())
    targets = file_list + list(out.glob("*.template.json"))
    assert list(out.glob("*.template.json"))

    # Explicitly verify Phase 15 compute files are scanned
    rel_paths = {p.relative_to(ROOT).as_posix() for p in file_list}
    expected_scanned = {
        "bootstrap/api.sh",
        "bootstrap/worker.sh",
        "bootstrap/common.sh",
        "bootstrap/systemd/lectify-api.service",
        "bootstrap/systemd/lectify-web.service",
        "bootstrap/systemd/lectify-worker.service",
        "lectify_cdk/compute_stack.py",
        "lectify_cdk/compute_iam.py",
        "scripts/vendor-ffmpeg.sh",
    }
    missing = expected_scanned - rel_paths
    assert not missing, f"Expected files not scanned by hygiene checker: {missing}"

    for p in targets:
        if p.name == "test_secrets_hygiene.py":
            continue
        text = p.read_text(errors="ignore")
        for pat in PATTERNS:
            assert not re.search(pat, text), f"secret-like match {pat} in {p}"


def test_no_cost_traps_in_synth(tmp_path):
    out = _synth(tmp_path)
    types = {}
    for t in out.glob("*.template.json"):
        for r in json.loads(t.read_text()).get("Resources", {}).values():
            if r["Type"] == "AWS::EC2::VPCEndpoint":
                assert r["Properties"].get("VpcEndpointType") == "Gateway", "interface endpoint found"
            types[r["Type"]] = types.get(r["Type"], 0) + 1
    assert "AWS::EC2::NatGateway" not in types
    assert "AWS::EC2::EIP" not in types


def test_put_secrets_script_structure():
    p = ROOT / "scripts" / "put-secrets.sh"
    s = p.read_text()
    assert os.access(p, os.X_OK)
    for k in ("/lectify/", "JWT_SECRET", "GROQ_API_KEY", "GEMINI_API_KEY", "SecureString", "--overwrite", "--help", "read -r -s"):
        assert k in s
    assert not re.search(r"echo[^\n]*\$\{?(VAL|!KEY)", s)
    r = subprocess.run(["bash", str(p), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "Usage" in r.stdout
