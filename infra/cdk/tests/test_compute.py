"""Tests for ComputeStack ALB, target groups, ASGs, launch templates, and user-data wiring."""
import tempfile
from pathlib import Path
import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from lectify_cdk.compute_stack import ComputeStack, WORKER_MAX
from lectify_cdk.data_stack import DataStack
from lectify_cdk.network_stack import NetworkStack


def make_stack(stub_dir: Path | None = None):
    """Build Network + Data + Compute stacks in a fresh App with asset stubs."""
    if stub_dir is None:
        _tmp = tempfile.TemporaryDirectory()
        stub_dir = Path(_tmp.name)

    backend_dir = stub_dir / "backend"
    backend_dir.mkdir(parents=True, exist_ok=True)
    (backend_dir / "requirements.txt").write_text("# stub requirements\nfastapi\n")
    (backend_dir / "server.py").write_text("# stub server\n")

    web_dir = stub_dir / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    (web_dir / "server.js").write_text("// stub server\n")

    bootstrap_dir = stub_dir / "bootstrap"
    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    (bootstrap_dir / "api.sh").write_text("#!/bin/bash\n")
    (bootstrap_dir / "worker.sh").write_text("#!/bin/bash\n")

    ffmpeg_archive = stub_dir / "ffmpeg-release-amd64-static.tar.xz"
    ffmpeg_archive.write_bytes(b"stub-archive")

    app = cdk.App()
    env = cdk.Environment(account="123456789012", region="ap-southeast-2")
    net = NetworkStack(app, "N", env=env)
    data = DataStack(
        app,
        "D",
        network=net,
        app_origin="http://localhost:3000",
        ready_emails=["alerts@example.com"],
        env=env,
    )
    compute = ComputeStack(
        app,
        "C",
        network=net,
        data=data,
        backend_dir=str(backend_dir),
        web_dir=str(web_dir),
        bootstrap_dir=str(bootstrap_dir),
        ffmpeg_archive=str(ffmpeg_archive),
        env=env,
    )
    return compute, Template.from_stack(compute), Template.from_stack(net)


@pytest.fixture(scope="module")
def stacks():
    with tempfile.TemporaryDirectory() as td:
        yield make_stack(Path(td))


@pytest.fixture(scope="module")
def compute_stack(stacks):
    return stacks[0]


@pytest.fixture(scope="module")
def t(stacks):
    return stacks[1]


@pytest.fixture(scope="module")
def t_net(stacks):
    return stacks[2]


def test_alb_configuration(t, t_net):
    t.resource_count_is("AWS::ElasticLoadBalancingV2::LoadBalancer", 1)
    albs = t.find_resources("AWS::ElasticLoadBalancingV2::LoadBalancer")
    alb = next(iter(albs.values()))
    props = alb["Properties"]

    assert props["Scheme"] == "internet-facing"
    assert props["Type"] == "application"
    attrs = {a["Key"]: a["Value"] for a in props.get("LoadBalancerAttributes", [])}
    assert attrs.get("routing.http.drop_invalid_header_fields.enabled") == "true"

    sgs = props["SecurityGroups"]
    assert len(sgs) == 1
    subnets = props["Subnets"]
    assert len(subnets) == 2


def test_target_groups_configuration(t):
    t.resource_count_is("AWS::ElasticLoadBalancingV2::TargetGroup", 2)
    tgs = t.find_resources("AWS::ElasticLoadBalancingV2::TargetGroup")

    web_tgs = [tg for tg in tgs.values() if tg["Properties"].get("Port") == 3000]
    api_tgs = [tg for tg in tgs.values() if tg["Properties"].get("Port") == 8000]

    assert len(web_tgs) == 1, "Expected 1 web target group on port 3000"
    assert len(api_tgs) == 1, "Expected 1 API target group on port 8000"

    for tg in (web_tgs[0], api_tgs[0]):
        props = tg["Properties"]
        assert props["Protocol"] == "HTTP"
        assert props["TargetType"] == "instance"
        assert props["HealthCheckPath"] == "/healthz"
        assert props["HealthCheckIntervalSeconds"] == 15
        assert props["HealthyThresholdCount"] == 2
        assert props["UnhealthyThresholdCount"] == 3
        attrs = {a["Key"]: a["Value"] for a in props.get("TargetGroupAttributes", [])}
        assert attrs.get("deregistration_delay.timeout_seconds") == "30"


def test_listener_and_routing_rules(t):
    t.resource_count_is("AWS::ElasticLoadBalancingV2::Listener", 1)
    listeners = t.find_resources("AWS::ElasticLoadBalancingV2::Listener")
    listener = next(iter(listeners.values()))
    l_props = listener["Properties"]

    assert l_props["Port"] == 80
    assert l_props["Protocol"] == "HTTP"

    default_actions = l_props["DefaultActions"]
    assert len(default_actions) == 1
    assert default_actions[0]["Type"] == "forward"

    t.resource_count_is("AWS::ElasticLoadBalancingV2::ListenerRule", 1)
    rules = t.find_resources("AWS::ElasticLoadBalancingV2::ListenerRule")
    rule = next(iter(rules.values()))
    r_props = rule["Properties"]

    assert r_props["Priority"] == 10
    assert r_props["Actions"][0]["Type"] == "forward"

    conditions = r_props["Conditions"]
    path_conds = [c for c in conditions if c.get("Field") == "path-pattern"]
    assert len(path_conds) == 1
    assert "/api/*" in path_conds[0].get("Values", []) or "/api/*" in path_conds[0].get("PathPatternConfig", {}).get("Values", [])


def test_stack_outputs_and_no_exports(t):
    outputs = t.find_outputs("*")
    assert "AlbDnsName" in outputs

    for out_name, out_data in outputs.items():
        assert "Export" not in out_data, f"Output {out_name} has unexpected Export"


def test_launch_templates(t):
    t.resource_count_is("AWS::EC2::LaunchTemplate", 2)
    lts = t.find_resources("AWS::EC2::LaunchTemplate")

    for lt in lts.values():
        data = lt["Properties"]["LaunchTemplateData"]
        # IMDSv2
        meta = data["MetadataOptions"]
        assert meta["HttpTokens"] == "required"
        assert meta["HttpPutResponseHopLimit"] == 1

        # No KeyName
        assert "KeyName" not in data

        # Encrypted gp3 root volume
        bd = data["BlockDeviceMappings"][0]
        ebs = bd["Ebs"]
        assert ebs["Encrypted"] is True
        assert ebs["VolumeType"] == "gp3"
        assert ebs["VolumeSize"] == 20
        assert ebs["DeleteOnTermination"] is True

        # Public IP
        ni = data["NetworkInterfaces"][0]
        assert ni["AssociatePublicIpAddress"] is True

        # Instance type
        assert data["InstanceType"] == "t3.small"


def test_web_asg(t):
    asgs = t.find_resources("AWS::AutoScaling::AutoScalingGroup")
    web_asgs = [a for a in asgs.values() if a["Properties"].get("HealthCheckType") == "ELB"]
    assert len(web_asgs) == 1, "Expected 1 web ASG with ELB health check"
    props = web_asgs[0]["Properties"]

    assert props["MinSize"] == "1"
    assert props["MaxSize"] == "2"
    assert props["DesiredCapacity"] == "1"
    assert props["HealthCheckGracePeriod"] == 300
    assert len(props["VPCZoneIdentifier"]) == 2
    # Attached to both target groups
    assert len(props.get("TargetGroupARNs", [])) == 2


def test_worker_asg(t):
    asgs = t.find_resources("AWS::AutoScaling::AutoScalingGroup")
    worker_asgs = [a for a in asgs.values() if a["Properties"].get("HealthCheckType") == "EC2"]
    assert len(worker_asgs) == 1, "Expected 1 worker ASG with EC2 health check"
    props = worker_asgs[0]["Properties"]

    assert props["MinSize"] == "1"
    assert int(props["MaxSize"]) == WORKER_MAX
    assert int(props["MaxSize"]) <= 3, "Worker ASG must be hard-capped at 3"
    assert props["DesiredCapacity"] == "1"
    assert len(props["VPCZoneIdentifier"]) == 2
    assert "TargetGroupARNs" not in props or len(props.get("TargetGroupARNs", [])) == 0


def test_asg_cfn_signals(t):
    asgs = t.find_resources("AWS::AutoScaling::AutoScalingGroup")
    for asg in asgs.values():
        cp = asg.get("CreationPolicy", {})
        assert "ResourceSignal" in cp
        assert cp["ResourceSignal"].get("Timeout") == "PT20M"


def test_user_data_hygiene(t):
    lts = t.find_resources("AWS::EC2::LaunchTemplate")
    for lt in lts.values():
        ud = lt["Properties"]["LaunchTemplateData"]["UserData"]
        # decode base64 if dict or extract joined string
        ud_str = str(ud)

        # Thinness & non-secret assertions
        assert "aws-cfn-bootstrap" in ud_str
        assert "JWT_SECRET" not in ud_str
        assert "GROQ_API_KEY" not in ud_str
        assert "GEMINI_API_KEY" not in ud_str
        assert "password" not in ud_str.lower()
        # No inline heavy app logic
        assert "uvicorn" not in ud_str
        assert "systemctl" not in ud_str
