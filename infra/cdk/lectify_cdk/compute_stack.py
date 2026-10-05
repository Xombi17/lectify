"""Compute tier stack: ALB, target groups, listener rules, and instance IAM roles."""
import aws_cdk as cdk
from aws_cdk import CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from constructs import Construct

from lectify_cdk.compute_iam import build_api_role, build_worker_role


class ComputeStack(Stack):
    """ALB, target groups, routing rules, and least-privilege IAM roles for compute instances."""

    def __init__(
        self,
        scope: Construct,
        cid: str,
        *,
        network,
        data,
        **kw,
    ):
        super().__init__(scope, cid, **kw)
        Tags.of(self).add("Project", "lectify")

        # 1. Internet-facing Application Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=network.vpc,
            internet_facing=True,
            security_group=network.sg_alb,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            idle_timeout=Duration.seconds(60),
            drop_invalid_header_fields=True,
        )

        # 2. Web Target Group (:3000)
        self.web_tg = elbv2.ApplicationTargetGroup(
            self,
            "WebTg",
            vpc=network.vpc,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=3000,
            health_check=elbv2.HealthCheck(
                path="/healthz",
                interval=Duration.seconds(15),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        # 3. API Target Group (:8000)
        self.api_tg = elbv2.ApplicationTargetGroup(
            self,
            "ApiTg",
            vpc=network.vpc,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTP,
            port=8000,
            health_check=elbv2.HealthCheck(
                path="/healthz",
                interval=Duration.seconds(15),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
        )

        # 4. HTTP:80 Listener — DO NOT set open=True (network.sg_alb already allows 80)
        self.listener = self.alb.add_listener(
            "HttpListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            open=False,
            default_target_groups=[self.web_tg],
        )

        # Route /api/* to the API Target Group
        self.listener.add_target_groups(
            "ApiRule",
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/api/*"])],
            target_groups=[self.api_tg],
        )

        # 5. Least-privilege IAM roles
        self.api_role = build_api_role(self, data)
        self.worker_role = build_worker_role(self, data)

        # 6. Outputs
        CfnOutput(self, "AlbDnsName", value=self.alb.load_balancer_dns_name)
