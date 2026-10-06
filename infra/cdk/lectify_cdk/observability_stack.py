"""Observability: log groups, dead-letter filter, ops alarms, queue-backlog step scaling, dashboard."""
from aws_cdk import Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_logs as logs
from constructs import Construct

from lectify_cdk.compute_iam import LOG_GROUP_API, LOG_GROUP_WEB, LOG_GROUP_WORKER

FIVE = Duration.minutes(5)
ONE = Duration.minutes(1)


class ObservabilityStack(Stack):
    def __init__(self, scope: Construct, cid: str, *, data, compute, budget, **kw) -> None:
        super().__init__(scope, cid, **kw)
        Tags.of(self).add("Project", "lectify")

        def ctx(key: str, default: float) -> float:
            return float(self.node.try_get_context(key) or default)

        # Log groups (7-day retention, destroyed with stack)
        groups = {}
        for cid_, name in (("Api", LOG_GROUP_API), ("Web", LOG_GROUP_WEB), ("Worker", LOG_GROUP_WORKER)):
            groups[name] = logs.LogGroup(
                self, f"{cid_}Logs", log_group_name=name,
                retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY,
            )
        self.worker_log_group = groups[LOG_GROUP_WORKER]

        dl_filter = logs.MetricFilter(
            self, "DeadLetterFilter", log_group=self.worker_log_group,
            filter_pattern=logs.FilterPattern.literal('"JOB_DEAD_LETTER"'),
            metric_namespace="Lectify", metric_name="DeadLetterJobs",
            metric_value="1", default_value=0,
        )
        dead_letter = dl_filter.metric(statistic="Sum", period=FIVE)

        def cpu(asg) -> cw.Metric:
            return cw.Metric(
                namespace="AWS/EC2", metric_name="CPUUtilization", statistic="Average", period=FIVE,
                dimensions_map={"AutoScalingGroupName": asg.auto_scaling_group_name},
            )

        q = data.queues
        api_5xx = cw.MathExpression(
            expression="FILL(e,0) + 10 * FILL(u,0)",
            using_metrics={
                "e": compute.api_tg.metric_http_code_target(
                    elbv2.HttpCodeTarget.TARGET_5XX_COUNT, statistic="Sum", period=FIVE),
                "u": compute.api_tg.metric_unhealthy_host_count(statistic="Maximum", period=FIVE),
            },
            period=FIVE, label="API 5xx + unhealthy",
        )

        specs = [
            ("lectify-transcribe-backlog-age",
             q["transcribe"].metric_approximate_age_of_oldest_message(statistic="Maximum", period=FIVE),
             ctx("obs_transcribe_age_s", 1800), 3),
            ("lectify-materials-backlog-depth",
             q["materials"].metric_approximate_number_of_messages_visible(statistic="Maximum", period=FIVE),
             ctx("obs_materials_depth", 20), 3),
            ("lectify-dlq-depth",
             data.dlq.metric_approximate_number_of_messages_visible(statistic="Maximum", period=FIVE),
             ctx("obs_dlq_threshold", 1), 1),
            ("lectify-worker-cpu-high", cpu(compute.worker_asg), ctx("obs_worker_cpu", 85), 3),
            ("lectify-web-cpu-high", cpu(compute.web_asg), ctx("obs_web_cpu", 80), 3),
            ("lectify-dead-letter-jobs", dead_letter, 1, 1),
            ("lectify-api-5xx-unhealthy", api_5xx, ctx("obs_api_5xx", 10), 1),
        ]
        action = cw_actions.SnsAction(budget.ops_topic)
        self.alarms = []
        for name, metric, threshold, periods in specs:
            a = cw.Alarm(
                self, "A" + name.replace("-", " ").title().replace(" ", ""),
                alarm_name=name, metric=metric, threshold=threshold, evaluation_periods=periods,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            a.add_alarm_action(action)
            a.add_ok_action(action)
            self.alarms.append(a)

        # Backlog = visible + in-flight over transcribe + materials only (embed excluded)
        def part(queue, vis: bool) -> cw.Metric:
            fn = (queue.metric_approximate_number_of_messages_visible if vis
                  else queue.metric_approximate_number_of_messages_not_visible)
            return fn(statistic="Maximum", period=ONE)

        self.backlog = cw.MathExpression(
            expression="ta+tb+ma+mb",
            using_metrics={
                "ta": part(q["transcribe"], True), "tb": part(q["transcribe"], False),
                "ma": part(q["materials"], True), "mb": part(q["materials"], False),
            },
            period=ONE, label="Pipeline backlog",
        )
        hi, hi2 = ctx("obs_scale_out_backlog", 5), ctx("obs_scale_out_backlog_high", 20)
        self.scale_out = autoscaling.StepScalingPolicy(
            self, "WorkerScaleOut", auto_scaling_group=compute.worker_asg, metric=self.backlog,
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            scaling_steps=[
                autoscaling.ScalingInterval(upper=hi, change=0),
                autoscaling.ScalingInterval(lower=hi, upper=hi2, change=1),
                autoscaling.ScalingInterval(lower=hi2, change=2),
            ],
            estimated_instance_warmup=Duration.seconds(int(ctx("obs_worker_warmup_s", 300))),
            evaluation_periods=2, datapoints_to_alarm=2,
        )
        lo, n = ctx("obs_scale_in_backlog", 1), int(ctx("obs_scale_in_minutes", 15))
        # ponytail: step scaling has no cooldown; long scale-in = n consecutive 1-min datapoints
        self.scale_in = autoscaling.StepScalingPolicy(
            self, "WorkerScaleIn", auto_scaling_group=compute.worker_asg, metric=self.backlog,
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            scaling_steps=[
                autoscaling.ScalingInterval(upper=lo, change=-1),
                autoscaling.ScalingInterval(lower=lo, change=0),
            ],
            evaluation_periods=n, datapoints_to_alarm=n,
        )

        # Dashboard
        queue_metrics = []
        for s, queue in q.items():
            queue_metrics += [part(queue, True), part(queue, False)]
        workers = cw.Metric(
            namespace="AWS/AutoScaling", metric_name="GroupInServiceInstances", statistic="Maximum",
            period=ONE, dimensions_map={"AutoScalingGroupName": compute.worker_asg.auto_scaling_group_name},
        )
        status_alarms = self.alarms + [a for a in (self.scale_out.upper_alarm, self.scale_in.lower_alarm) if a]
        dash = cw.Dashboard(self, "Overview", dashboard_name="lectify-overview")
        dash.add_widgets(cw.GraphWidget(title="Queue depth", left=queue_metrics, width=24))
        dash.add_widgets(
            cw.GraphWidget(title="DLQ depth", width=12, left=[
                data.dlq.metric_approximate_number_of_messages_visible(statistic="Maximum", period=FIVE)]),
            cw.GraphWidget(title="Dead-letter jobs", width=12, left=[dead_letter]),
        )
        dash.add_widgets(
            cw.GraphWidget(title="Worker count", width=12, left=[workers], right=[self.backlog]),
            cw.GraphWidget(title="CPU", width=12, left=[cpu(compute.worker_asg), cpu(compute.web_asg)]),
        )
        dash.add_widgets(cw.GraphWidget(title="ALB", width=24, left=[
            compute.api_tg.metric_request_count(statistic="Sum", period=FIVE),
            compute.api_tg.metric_http_code_target(
                elbv2.HttpCodeTarget.TARGET_5XX_COUNT, statistic="Sum", period=FIVE),
        ]))
        dash.add_widgets(cw.AlarmStatusWidget(title="Alarms", alarms=status_alarms, width=24))
