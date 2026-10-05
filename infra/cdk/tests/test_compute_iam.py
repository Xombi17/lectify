"""Tests for Compute tier IAM roles: least-privilege policies and wildcard guards."""
import pytest
from aws_cdk.assertions import Template

from tests.test_compute import make_stack


@pytest.fixture(scope="module")
def stacks():
    return make_stack()


@pytest.fixture(scope="module")
def t_compute(stacks):
    return stacks[1]


@pytest.fixture(scope="module")
def t_net(stacks):
    return stacks[2]


def _extract_resources(val):
    """Recursively extract string representations from CFN resource expressions."""
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        out = []
        for x in val:
            out.extend(_extract_resources(x))
        return out
    if isinstance(val, dict):
        if "Fn::Join" in val:
            sep, parts = val["Fn::Join"]
            extracted_parts = [_extract_resources(p) for p in parts]
            # flatten single parts
            flat = ["".join(p[0] if p else "" for p in extracted_parts)]
            return flat
        out = []
        for v in val.values():
            out.extend(_extract_resources(v))
        return out
    return []


def assert_wildcard_guard(template: Template):
    """Ensure no statement has Resource: '*' and wildcard tails are strictly allow-listed."""
    roles = template.find_resources("AWS::IAM::Role")
    policies = template.find_resources("AWS::IAM::Policy")

    all_statements = []

    # Check inline policies attached via Policy resources or Role.Policies
    for r in roles.values():
        for pol in r["Properties"].get("Policies", []):
            all_statements.extend(pol["PolicyDocument"].get("Statement", []))

    for p in policies.values():
        all_statements.extend(p["Properties"]["PolicyDocument"].get("Statement", []))

    allowed_wildcard_tails = (
        "/classes/*",
        "parameter/lectify/*",
    )

    assert len(all_statements) > 0, "No IAM statements found to validate"

    for stmt in all_statements:
        resources = _extract_resources(stmt.get("Resource", []))
        for res in resources:
            assert res != "*", f"Disallowed bare wildcard Resource in statement: {stmt}"
            if "*" in res:
                is_allowed = any(
                    res.endswith(tail) for tail in allowed_wildcard_tails
                ) or (":s3:::cdk-" in res and res.endswith("/*"))
                assert is_allowed, f"Disallowed wildcard in Resource: {res} (stmt: {stmt})"


def test_iam_roles_basic_structure(t_compute):
    roles = t_compute.find_resources("AWS::IAM::Role")
    assert len(roles) == 2, "Expected exactly 2 IAM roles (API and Worker)"

    for r in roles.values():
        props = r["Properties"]
        # EC2 trust
        principals = props["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]
        assert principals.get("Service") == "ec2.amazonaws.com"
        # Managed policy
        mps = props.get("ManagedPolicyArns", [])
        assert any("AmazonSSMManagedInstanceCore" in str(mp) for mp in mps)


def test_iam_wildcard_guard(t_compute):
    """Assert all inline statements follow least-privilege wildcard restrictions."""
    assert_wildcard_guard(t_compute)


def test_api_role_permissions(t_compute):
    policies = t_compute.find_resources("AWS::IAM::Policy")
    api_policy = None
    for p_id, p in policies.items():
        if "ApiRole" in p_id or "ApiRoleDefaultPolicy" in p_id:
            api_policy = p
            break

    assert api_policy is not None, "ApiRoleDefaultPolicy not found"
    statements = api_policy["Properties"]["PolicyDocument"]["Statement"]

    all_actions = set()
    for stmt in statements:
        act = stmt["Action"]
        if isinstance(act, str):
            all_actions.add(act)
        elif isinstance(act, list):
            all_actions.update(act)

    # API role must have S3 Put/Get/Abort on classes/*, SQS SendMessage, SecretsManager, SSM
    assert "s3:PutObject" in all_actions
    assert "s3:GetObject" in all_actions
    assert "s3:AbortMultipartUpload" in all_actions
    assert "sqs:SendMessage" in all_actions
    assert "secretsmanager:GetSecretValue" in all_actions
    assert "ssm:GetParametersByPath" in all_actions

    # API role must NOT have worker consumer permissions or SNS publish
    assert "sqs:ReceiveMessage" not in all_actions
    assert "sqs:DeleteMessage" not in all_actions
    assert "sns:Publish" not in all_actions
    assert "s3:ListBucket" not in all_actions


def test_worker_role_permissions(t_compute):
    policies = t_compute.find_resources("AWS::IAM::Policy")
    worker_policy = None
    for p_id, p in policies.items():
        if "WorkerRole" in p_id or "WorkerRoleDefaultPolicy" in p_id:
            worker_policy = p
            break

    assert worker_policy is not None, "WorkerRoleDefaultPolicy not found"
    statements = worker_policy["Properties"]["PolicyDocument"]["Statement"]

    all_actions = set()
    for stmt in statements:
        act = stmt["Action"]
        if isinstance(act, str):
            all_actions.add(act)
        elif isinstance(act, list):
            all_actions.update(act)

    # Worker role must have S3 Get/Put + ListBucket, SQS consumer actions, SNS publish
    assert "s3:GetObject" in all_actions
    assert "s3:PutObject" in all_actions
    assert "s3:ListBucket" in all_actions
    assert "sqs:ReceiveMessage" in all_actions
    assert "sqs:DeleteMessage" in all_actions
    assert "sqs:ChangeMessageVisibility" in all_actions
    assert "sns:Publish" in all_actions
    assert "secretsmanager:GetSecretValue" in all_actions
    assert "ssm:GetParametersByPath" in all_actions


def test_no_ssh_ingress_and_no_nat(t_net):
    """Verify security posture: no port 22 SSH ingress and no NAT gateways/EIPs."""
    sgs = t_net.find_resources("AWS::EC2::SecurityGroup")
    for sg_id, sg in sgs.items():
        ingress_rules = sg["Properties"].get("SecurityGroupIngress", [])
        for rule in ingress_rules:
            from_port = rule.get("FromPort")
            to_port = rule.get("ToPort")
            if from_port is not None and to_port is not None:
                assert not (from_port <= 22 <= to_port), f"Port 22 SSH ingress found in {sg_id}"

    t_net.resource_count_is("AWS::EC2::NatGateway", 0)
    t_net.resource_count_is("AWS::EC2::EIP", 0)
