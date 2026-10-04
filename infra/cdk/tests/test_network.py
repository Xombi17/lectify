import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from lectify_cdk.network_stack import NetworkStack


@pytest.fixture(scope="module")
def tpl():
    stack = NetworkStack(cdk.App(), "N", env=cdk.Environment(account="123456789012", region="ap-south-1"))
    cdk.Tags.of(stack).add("Project", "lectify")
    return stack, Template.from_stack(stack)


def _res(t, type_):
    return t.find_resources(type_)


def test_no_nat_no_eip(tpl):
    _, t = tpl
    t.resource_count_is("AWS::EC2::NatGateway", 0)
    t.resource_count_is("AWS::EC2::EIP", 0)


def test_s3_gateway_endpoint_on_all_route_tables(tpl):
    _, t = tpl
    eps = _res(t, "AWS::EC2::VPCEndpoint")
    assert len(eps) == 1
    p = next(iter(eps.values()))["Properties"]
    assert p["VpcEndpointType"] == "Gateway"
    assert "s3" in str(p["ServiceName"])
    rts = set(_res(t, "AWS::EC2::RouteTable"))
    assert len(p["RouteTableIds"]) == 4
    assert {r["Ref"] for r in p["RouteTableIds"]} == rts


def test_vpc_and_subnets(tpl):
    _, t = tpl
    t.has_resource_properties("AWS::EC2::VPC", {"CidrBlock": "10.0.0.0/16"})
    subs = [r["Properties"] for r in _res(t, "AWS::EC2::Subnet").values()]
    assert len(subs) == 4
    assert all(s["CidrBlock"].endswith("/24") for s in subs)
    assert sum(1 for s in subs if s.get("MapPublicIpOnLaunch") is True) == 2
    assert len({str(s["AvailabilityZone"]) for s in subs}) == 2


def test_routes_only_public_via_igw(tpl):
    _, t = tpl
    t.resource_count_is("AWS::EC2::InternetGateway", 1)
    routes = [r["Properties"] for r in _res(t, "AWS::EC2::Route").values() if r["Properties"].get("DestinationCidrBlock") == "0.0.0.0/0"]
    assert len(routes) == 2
    assert all("GatewayId" in r and "NatGatewayId" not in r for r in routes)


def test_no_retain_tag_no_exports(tpl):
    _, t = tpl
    j = t.to_json()
    assert not [k for k, r in j["Resources"].items() if r.get("DeletionPolicy") == "Retain"]
    t.has_resource_properties("AWS::EC2::VPC", Match.object_like({"Tags": Match.array_with([{"Key": "Project", "Value": "lectify"}])}))
    assert not any("Export" in o for o in j.get("Outputs", {}).values())


def _ingress(stack, t):
    out = {}
    for lid, r in _res(t, "AWS::EC2::SecurityGroup").items():
        out.setdefault(lid, []).extend(r["Properties"].get("SecurityGroupIngress", []))
    for r in _res(t, "AWS::EC2::SecurityGroupIngress").values():
        p = r["Properties"]
        out.setdefault(p["GroupId"]["Fn::GetAtt"][0], []).append(p)
    return out


def _lid(stack, sg):
    return stack.get_logical_id(sg.node.default_child)


def _src(rule):
    s = rule["SourceSecurityGroupId"]
    return s["Fn::GetAtt"][0]


def test_four_sgs(tpl):
    _, t = tpl
    t.resource_count_is("AWS::EC2::SecurityGroup", 4)


def test_sg_rules(tpl):
    s, t = tpl
    ing = _ingress(s, t)
    alb, api, wk, rds = (_lid(s, x) for x in (s.sg_alb, s.sg_api, s.sg_worker, s.sg_rds))
    a = ing[alb]
    assert len(a) == 1 and a[0]["FromPort"] == 80 == a[0]["ToPort"] and a[0]["CidrIp"] == "0.0.0.0/0"
    assert len(ing[api]) == 2
    assert {r["FromPort"] for r in ing[api]} == {8000, 3000}
    assert all(_src(r) == alb and "CidrIp" not in r and "CidrIpv6" not in r for r in ing[api])
    assert ing.get(wk, []) == []
    assert len(ing[rds]) == 2
    assert all(r["FromPort"] == 5432 == r["ToPort"] and "CidrIp" not in r and "CidrIpv6" not in r for r in ing[rds])
    assert {_src(r) for r in ing[rds]} == {api, wk}


def test_no_ssh_no_other_cidr(tpl):
    s, t = tpl
    rules = [r for v in _ingress(s, t).values() for r in v]
    assert all(r["IpProtocol"] != "-1" and not (r["FromPort"] <= 22 <= r["ToPort"]) for r in rules)
    cidr = [r for r in rules if "CidrIp" in r or "CidrIpv6" in r]
    assert len(cidr) == 1 and cidr[0]["FromPort"] == 80
