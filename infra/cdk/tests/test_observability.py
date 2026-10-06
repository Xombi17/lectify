"""ObservabilityStack template tests."""
import json
import tempfile
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from lectify_cdk.budget_stack import BudgetStack
from lectify_cdk.observability_stack import ObservabilityStack
from tests.test_compute import make_stack


def build(context=None):
    out = {}

    def extra(app, env, data, compute):
        budget = BudgetStack(app, "B", email="ops@example.com", limit_usd=50, env=env)
        out["obs"] = ObservabilityStack(app, "O", data=data, compute=compute, budget=budget, env=env)

    with tempfile.TemporaryDirectory() as td:
        make_stack(Path(td), context, extra)
        return Template.from_stack(out["obs"])


@pytest.fixture(scope="module")
def t():
    return build()


def test_log_groups(t):
    for n in ("/lectify/api", "/lectify/web", "/lectify/worker"):
        t.has_resource("AWS::Logs::LogGroup", {
            "Properties": {"LogGroupName": n, "RetentionInDays": 7},
            "DeletionPolicy": "Delete",
        })
    t.resource_count_is("AWS::Logs::LogGroup", 3)


def test_metric_filter(t):
    t.has_resource_properties("AWS::Logs::MetricFilter", {
        "FilterPattern": Match.string_like_regexp("JOB_DEAD_LETTER"),
        "MetricTransformations": [Match.object_like({
            "MetricNamespace": "Lectify", "MetricName": "DeadLetterJobs",
            "MetricValue": "1", "DefaultValue": 0})],
    })


def test_alarms(t):
    alarms = t.find_resources("AWS::CloudWatch::Alarm")
    assert len(alarms) == 9 <= 10
    named = [a["Properties"] for a in alarms.values()
             if str(a["Properties"].get("AlarmName", "")).startswith("lectify-")]
    assert len(named) == 7
    for p in named:
        assert len(p["AlarmActions"]) == 1 and len(p["OKActions"]) == 1
        assert p["TreatMissingData"] == "notBreaching"


def test_step_scaling(t):
    pols = t.find_resources("AWS::AutoScaling::ScalingPolicy")
    assert len(pols) == 2
    props = [p["Properties"] for p in pols.values()]
    assert all(p["PolicyType"] == "StepScaling" and p["AdjustmentType"] == "ChangeInCapacity"
               for p in props)
    assert any(p.get("EstimatedInstanceWarmup") == 300 for p in props)


def test_scaling_alarms(t):
    alarms = [a["Properties"] for a in t.find_resources("AWS::CloudWatch::Alarm").values()
              if "AlarmName" not in a["Properties"]]
    assert len(alarms) == 2
    for a in alarms:
        s = json.dumps(a["Metrics"])
        assert "ta+tb+ma+mb" in s and "lectify-embed" not in s
    out = next(a for a in alarms if a["ComparisonOperator"] == "GreaterThanOrEqualToThreshold")
    assert out["Threshold"] == 5
    inn = next(a for a in alarms if a["ComparisonOperator"] == "LessThanOrEqualToThreshold")
    assert (inn["EvaluationPeriods"], inn["DatapointsToAlarm"], inn["Threshold"]) == (15, 15, 1)


def test_context_override():
    t2 = build({"obs_dlq_threshold": "3"})
    t2.has_resource_properties("AWS::CloudWatch::Alarm",
                               {"AlarmName": "lectify-dlq-depth", "Threshold": 3})


def test_dashboard(t):
    t.resource_count_is("AWS::CloudWatch::Dashboard", 1)
    t.has_resource_properties("AWS::CloudWatch::Dashboard", {"DashboardName": "lectify-overview"})
    body = json.dumps(list(t.find_resources("AWS::CloudWatch::Dashboard").values())[0]["Properties"]["DashboardBody"])
    for s in ("ApproximateNumberOfMessagesVisible", "ApproximateNumberOfMessagesNotVisible",
              "GroupInServiceInstances", "CPUUtilization", "DeadLetterJobs",
              "HTTPCode_Target_5XX_Count", "RequestCount", '\\"type\\":\\"alarm\\"'):
        assert s in body, s
