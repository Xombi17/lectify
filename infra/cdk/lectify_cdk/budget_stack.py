from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_budgets as budgets,
    aws_iam as iam,
    aws_kms as kms,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)
from constructs import Construct


def _note(kind: str, pct: int, email: str, topic_arn: str):
    return budgets.CfnBudget.NotificationWithSubscribersProperty(
        notification=budgets.CfnBudget.NotificationProperty(
            notification_type=kind,
            comparison_operator="GREATER_THAN",
            threshold=pct,
            threshold_type="PERCENTAGE",
        ),
        subscribers=[
            budgets.CfnBudget.SubscriberProperty(subscription_type="EMAIL", address=email),
            budgets.CfnBudget.SubscriberProperty(subscription_type="SNS", address=topic_arn),
        ],
    )


class BudgetStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, email: str, limit_usd: float, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        acct = {"StringEquals": {"aws:SourceAccount": self.account}}
        svc = [iam.ServicePrincipal("cloudwatch.amazonaws.com"), iam.ServicePrincipal("budgets.amazonaws.com")]
        # CMK (not alias/aws/sns): the AWS-managed key blocks CloudWatch/Budgets delivery.
        key = kms.Key(
            self,
            "OpsTopicKey",
            alias="alias/lectify-ops",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
            pending_window=Duration.days(7),
        )
        key.add_to_resource_policy(
            iam.PolicyStatement(
                principals=svc,
                actions=["kms:Decrypt", "kms:GenerateDataKey*"],
                resources=["*"],
                conditions=acct,
            )
        )
        self.ops_topic = sns.Topic(self, "OpsTopic", topic_name="lectify-ops", master_key=key)
        self.ops_topic.add_subscription(subs.EmailSubscription(email))
        arn = self.ops_topic.topic_arn
        self.ops_topic.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[iam.ServicePrincipal("budgets.amazonaws.com")],
                actions=["sns:Publish"],
                resources=[arn],
                conditions={**acct, "ArnLike": {"aws:SourceArn": f"arn:{self.partition}:budgets::{self.account}:*"}},
            )
        )
        self.ops_topic.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
                actions=["sns:Publish"],
                resources=[arn],
                conditions=acct,
            )
        )
        # Credits/refunds excluded: otherwise credit-covered spend nets to $0 and never alerts.
        budget = budgets.CfnBudget(
            self,
            "Monthly",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_name="lectify-monthly",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=limit_usd, unit="USD"),
                cost_types=budgets.CfnBudget.CostTypesProperty(include_credit=False, include_refund=False),
            ),
            notifications_with_subscribers=[
                _note("ACTUAL", 50, email, arn),
                _note("ACTUAL", 80, email, arn),
                _note("ACTUAL", 100, email, arn),
                _note("FORECASTED", 100, email, arn),
            ],
        )
        budget.node.add_dependency(self.ops_topic.node.find_child("Policy"))
