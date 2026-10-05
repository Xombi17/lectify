import json
import subprocess
import sys
import pytest
from httpx import AsyncClient, ASGITransport
from server import app

@pytest.mark.asyncio
async def test_health_route_no_redis():
    """Verify that /api/health no longer checks redis or has it in the payload."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "redis" not in data["checks"]
    assert data["status"] == "ok"

def test_no_redis_arq_in_runtime():
    """Verify that importing server and workers does not load redis or arq."""
    code = (
        "import sys\n"
        "import server\n"
        "import workers.transcription\n"
        "import workers.ai\n"
        "import workers.embedding\n"
        "import json\n"
        "print(json.dumps({'redis': 'redis' in sys.modules, 'arq': 'arq' in sys.modules}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True
    )
    modules = json.loads(result.stdout)
    assert modules["redis"] is False, "redis was imported by the runtime"
    assert modules["arq"] is False, "arq was imported by the runtime"

def test_requirements_no_redis_arq():
    """Verify that requirements.txt does not pin redis or arq."""
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split("=")[0].split(">")[0].split("<")[0]
        assert pkg.lower() not in ["redis", "arq"], f"Found forbidden dependency in requirements: {line}"
