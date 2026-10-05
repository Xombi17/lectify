"""Tests for ComputeStack ALB, target groups, and listener routing rules."""
import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from lectify_cdk.compute_stack import ComputeStack
from lectify_cdk.data_stack import DataStack
from lectify_cdk.network_stack import NetworkStack


def make_stack():
    """Build Network + Data + Compute stacks in a fresh App."""
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
        env=env,
    )
    return compute, Template.from_stack(compute), Template.from_stack(net)


@pytest.fixture(scope="module")
def stacks():
    return make_stack()


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

    # Security groups must only be sg_alb
    sgs = props["SecurityGroups"]
    assert len(sgs) == 1

    # Subnets must be the two public subnets
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
        # TargetGroupAttributes: deregistration_delay.timeout_seconds = 30
        attrs = {a["Key"]: a["Value"] for a in props.get("TargetGroupAttributes", [])}
        assert attrs.get("deregistration_delay.timeout_seconds") == "30"


def test_listener_and_routing_rules(t):
    t.resource_count_is("AWS::ElasticLoadBalancingV2::Listener", 1)
    listeners = t.find_resources("AWS::ElasticLoadBalancingV2::Listener")
    listener = next(iter(listeners.values()))
    l_props = listener["Properties"]

    assert l_props["Port"] == 80
    assert l_props["Protocol"] == "HTTP"

    # Default action must forward to web target group (port 3000)
    default_actions = l_props["DefaultActions"]
    assert len(default_actions) == 1
    assert default_actions[0]["Type"] == "forward"

    # Rule priority 10 for /api/* -> API target group
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

    # Verify no CloudFormation Exports are created (tightly coupled by object ref)
    for out_name, out_data in outputs.items():
        assert "Export" not in out_data, f"Output {out_name} has unexpected Export"
