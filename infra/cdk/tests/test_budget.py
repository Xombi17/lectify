import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from lectify_cdk.budget_stack import BudgetStack

ENV = cdk.Environment(account="123456789012", region="ap-south-1")


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
    notes = budget["Properties"]["NotificationsWithSubscribers"]
    assert len(notes) == 4
    assert {(n["Notification"]["NotificationType"], n["Notification"]["Threshold"]) for n in notes} == {
        ("ACTUAL", 50), ("ACTUAL", 80), ("ACTUAL", 100), ("FORECASTED", 100)
    }
    for n in notes:
        assert n["Notification"]["ComparisonOperator"] == "GREATER_THAN"
        assert n["Notification"]["ThresholdType"] == "PERCENTAGE"
        assert n["Subscribers"] == [{"SubscriptionType": "EMAIL", "Address": "ops@example.com"}]


def test_limit_configurable():
    _tpl(120).has_resource_properties(
        "AWS::Budgets::Budget", {"Budget": Match.object_like({"BudgetLimit": {"Amount": 120, "Unit": "USD"}})}
    )


def test_no_sns_no_retain():
    t = _tpl()
    t.resource_count_is("AWS::SNS::Topic", 0)
    for r in t.to_json().get("Resources", {}).values():
        assert r.get("DeletionPolicy") != "Retain"
