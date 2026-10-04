from aws_cdk import Stack, aws_budgets as budgets
from constructs import Construct


def _note(kind: str, pct: int, email: str):
    return budgets.CfnBudget.NotificationWithSubscribersProperty(
        notification=budgets.CfnBudget.NotificationProperty(
            notification_type=kind,
            comparison_operator="GREATER_THAN",
            threshold=pct,
            threshold_type="PERCENTAGE",
        ),
        subscribers=[budgets.CfnBudget.SubscriberProperty(subscription_type="EMAIL", address=email)],
    )


class BudgetStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, email: str, limit_usd: float, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # Credits/refunds excluded: otherwise credit-covered spend nets to $0 and never alerts.
        budgets.CfnBudget(
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
                _note("ACTUAL", 50, email),
                _note("ACTUAL", 80, email),
                _note("ACTUAL", 100, email),
                _note("FORECASTED", 100, email),
            ],
        )
