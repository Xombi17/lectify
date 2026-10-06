import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from lectify_cdk.budget_stack import BudgetStack

ENV = cdk.Environment(account="123456789012", region="ap-southeast-2")


def _tpl(limit=50):
    stack = BudgetStack(cdk.App(), "B", email="ops@example.com", limit_usd=limit, env=ENV)
    return Template.from_stack(stack)


def test_budget_props():
    t = _tpl()
    t.resource_count_is("AWS::Budgets::Budget", 1)
    t.has_resource_properties(
        "AWS::Budgets::Budget",
        {
            "Budget": {
                "BudgetType": "COST",
                "TimeUnit": "MONTHLY",
                "BudgetName": "lectify-monthly",
                "BudgetLimit": {"Amount": 50, "Unit": "USD"},
                "CostTypes": Match.object_like({"IncludeCredit": False, "IncludeRefund": False}),
            }
        },
    )


def test_notifications():
    t = _tpl()
    budget = next(iter(t.find_resources("AWS::Budgets::Budget").values()))
    topic_id = next(iter(t.find_resources("AWS::SNS::Topic")))
    notes = budget["Properties"]["NotificationsWithSubscribers"]
    assert len(notes) == 4
    assert {(n["Notification"]["NotificationType"], n["Notification"]["Threshold"]) for n in notes} == {
        ("ACTUAL", 50), ("ACTUAL", 80), ("ACTUAL", 100), ("FORECASTED", 100)
    }
    for n in notes:
        assert n["Notification"]["ComparisonOperator"] == "GREATER_THAN"
        assert n["Notification"]["ThresholdType"] == "PERCENTAGE"
        assert len(n["Subscribers"]) == 2
        assert n["Subscribers"][0] == {"SubscriptionType": "EMAIL", "Address": "ops@example.com"}
        sns_sub = n["Subscribers"][1]
        assert sns_sub["SubscriptionType"] == "SNS"
        assert sns_sub["Address"] == {"Ref": topic_id}


def test_limit_configurable():
    _tpl(120).has_resource_properties(
        "AWS::Budgets::Budget", {"Budget": Match.object_like({"BudgetLimit": {"Amount": 120, "Unit": "USD"}})}
    )


def test_ops_topic_no_retain():
    t = _tpl()
    t.resource_count_is("AWS::SNS::Topic", 1)
    topic = next(iter(t.find_resources("AWS::SNS::Topic").values()))
    assert "KmsMasterKeyId" in topic["Properties"]
    assert "alias/aws/sns" not in str(topic["Properties"]["KmsMasterKeyId"])
    for r in t.to_json().get("Resources", {}).values():
        assert r.get("DeletionPolicy") != "Retain"


def test_ops_topic_key_policy():
    t = _tpl()
    t.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})
    key = next(iter(t.find_resources("AWS::KMS::Key").values()))
    st = [
        s for s in key["Properties"]["KeyPolicy"]["Statement"]
        if s["Principal"].get("Service") == ["cloudwatch.amazonaws.com", "budgets.amazonaws.com"]
    ]
    assert len(st) == 1
    assert st[0]["Action"] == ["kms:Decrypt", "kms:GenerateDataKey*"]
    assert st[0]["Condition"] == {"StringEquals": {"aws:SourceAccount": "123456789012"}}


def test_ops_topic_policy_principals():
    t = _tpl()
    pol = next(iter(t.find_resources("AWS::SNS::TopicPolicy").values()))
    st = pol["Properties"]["PolicyDocument"]["Statement"]
    svcs = {s["Principal"]["Service"] for s in st if s["Action"] == "sns:Publish"}
    assert svcs == {"budgets.amazonaws.com", "cloudwatch.amazonaws.com"}
    for s in st:
        if s["Action"] == "sns:Publish":
            assert s["Condition"]["StringEquals"]["aws:SourceAccount"] == "123456789012"


def test_ops_email_subscription():
    _tpl().has_resource_properties(
        "AWS::SNS::Subscription", {"Protocol": "email", "Endpoint": "ops@example.com"}
    )
    _tpl().resource_count_is("AWS::SNS::Subscription", 1)
