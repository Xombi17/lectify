"""Compute tier stack: ALB, target groups, ASGs, launch templates, assets, and IAM roles."""
from pathlib import Path
from typing import Optional
import aws_cdk as cdk
from aws_cdk import CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct

from lectify_cdk.compute_iam import build_api_role, build_worker_role

WORKER_MAX: int = 3


class ComputeStack(Stack):
    """ALB, target groups, routing rules, AutoScalingGroups, and launch templates."""

    def __init__(
        self,
        scope: Construct,
        cid: str,
        *,
        network,
        data,
        backend_dir: Optional[str] = None,
        web_dir: Optional[str] = None,
        bootstrap_dir: Optional[str] = None,
        ffmpeg_archive: Optional[str] = None,
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

        # 6. S3 Assets (packaged code bundles)
        self.backend_asset = None
        self.web_asset = None
        self.bootstrap_asset = None
        self.ffmpeg_asset = None

        if backend_dir and Path(backend_dir).exists():
            self.backend_asset = s3_assets.Asset(
                self,
                "BackendAsset",
                path=backend_dir,
                exclude=[
                    ".venv",
                    ".venv/*",
                    "tests",
                    "tests/*",
                    "__pycache__",
                    "__pycache__/*",
                    "storage_data",
                    "storage_data/*",
                    ".env*",
                ],
            )
            self.backend_asset.grant_read(self.api_role)
            self.backend_asset.grant_read(self.worker_role)

        if web_dir and Path(web_dir).exists():
            self.web_asset = s3_assets.Asset(
                self,
                "WebAsset",
                path=web_dir,
            )
            self.web_asset.grant_read(self.api_role)

        if bootstrap_dir and Path(bootstrap_dir).exists():
            self.bootstrap_asset = s3_assets.Asset(
                self,
                "BootstrapAsset",
                path=bootstrap_dir,
            )
            self.bootstrap_asset.grant_read(self.api_role)
            self.bootstrap_asset.grant_read(self.worker_role)

        if ffmpeg_archive and Path(ffmpeg_archive).exists():
            self.ffmpeg_asset = s3_assets.Asset(
                self,
                "FfmpegAsset",
                path=ffmpeg_archive,
            )
            self.ffmpeg_asset.grant_read(self.worker_role)

        # 7. UserData & Launch Templates
        al2023_image = ec2.MachineImage.latest_amazon_linux2023()
        t3_small = ec2.InstanceType("t3.small")

        block_devices = [
            ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=20,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    encrypted=True,
                    delete_on_termination=True,
                ),
            )
        ]

        self.web_user_data = ec2.UserData.for_linux()
        self.worker_user_data = ec2.UserData.for_linux()

        # Web Tier Launch Template
        self.web_lt = ec2.LaunchTemplate(
            self,
            "WebLaunchTemplate",
            machine_image=al2023_image,
            instance_type=t3_small,
            role=self.api_role,
            security_group=network.sg_api,
            require_imdsv2=True,
            http_put_response_hop_limit=1,
            associate_public_ip_address=True,
            block_devices=block_devices,
            user_data=self.web_user_data,
        )

        # Worker Tier Launch Template
        self.worker_lt = ec2.LaunchTemplate(
            self,
            "WorkerLaunchTemplate",
            machine_image=al2023_image,
            instance_type=t3_small,
            role=self.worker_role,
            security_group=network.sg_worker,
            require_imdsv2=True,
            http_put_response_hop_limit=1,
            associate_public_ip_address=True,
            block_devices=block_devices,
            user_data=self.worker_user_data,
        )

        # 8. AutoScalingGroups
        # NOTE: worker ASG omits desired_capacity on purpose: step scaling (ObservabilityStack) owns it,
        # so redeploys do not reset scaled capacity (D-09; costly to reverse). Web ASG stays fixed.
        self.web_asg = autoscaling.AutoScalingGroup(
            self,
            "WebAsg",
            vpc=network.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            launch_template=self.web_lt,
            min_capacity=1,
            max_capacity=2,
            desired_capacity=1,
            health_check=autoscaling.HealthCheck.elb(grace=Duration.seconds(300)),
            signals=autoscaling.Signals.wait_for_all(timeout=Duration.minutes(20)),
        )
        self.web_tg.add_target(self.web_asg)
        self.api_tg.add_target(self.web_asg)

        self.worker_asg = autoscaling.AutoScalingGroup(
            self,
            "WorkerAsg",
            vpc=network.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            launch_template=self.worker_lt,
            min_capacity=1,
            max_capacity=WORKER_MAX,
            group_metrics=[autoscaling.GroupMetrics.all()],
            health_check=autoscaling.HealthCheck.ec2(),
            signals=autoscaling.Signals.wait_for_all(timeout=Duration.minutes(20)),
        )

        # 9. Thin user-data wiring with CFN signals
        self._wire_user_data(data)

        # 10. Outputs
        CfnOutput(self, "AlbDnsName", value=self.alb.load_balancer_dns_name)

    def _wire_user_data(self, data):
        alb_dns = self.alb.load_balancer_dns_name

        def _build_commands(tier: str) -> list[str]:
            cmds = [
                "dnf install -y aws-cfn-bootstrap unzip",
                "mkdir -p /opt/lectify/bootstrap",
            ]
            if self.bootstrap_asset:
                cmds.extend([
                    f"aws s3 cp s3://{self.bootstrap_asset.s3_bucket_name}/{self.bootstrap_asset.s3_object_key} /tmp/bootstrap.zip",
                    "unzip -q -o /tmp/bootstrap.zip -d /opt/lectify/bootstrap",
                    "rm -f /tmp/bootstrap.zip",
                ])

            if self.backend_asset:
                cmds.append(f'export BACKEND_ASSET_BUCKET="{self.backend_asset.s3_bucket_name}"')
                cmds.append(f'export BACKEND_ASSET_KEY="{self.backend_asset.s3_object_key}"')

            if tier == "web" and self.web_asset:
                cmds.append(f'export WEB_ASSET_BUCKET="{self.web_asset.s3_bucket_name}"')
                cmds.append(f'export WEB_ASSET_KEY="{self.web_asset.s3_object_key}"')

            if tier == "worker" and self.ffmpeg_asset:
                cmds.append(f'export FFMPEG_ASSET_BUCKET="{self.ffmpeg_asset.s3_bucket_name}"')
                cmds.append(f'export FFMPEG_ASSET_KEY="{self.ffmpeg_asset.s3_object_key}"')

            cmds.extend([
                f'export DB_SECRET_ARN="{data.db.secret.secret_arn}"',
                f'export DB_HOST="{data.db.db_instance_endpoint_address}"',
                f'export DB_PORT="{data.db.db_instance_endpoint_port}"',
                'export DATABASE_NAME="postgres"',
                f'export QUEUE_URL_TRANSCRIBE="{data.queues["transcribe"].queue_url}"',
                f'export QUEUE_URL_MATERIALS="{data.queues["materials"].queue_url}"',
                f'export QUEUE_URL_EMBED="{data.queues["embed"].queue_url}"',
                f'export QUEUE_URL_DLQ="{data.dlq.queue_url}"',
                f'export LECTURE_READY_TOPIC_ARN="{data.topic.topic_arn}"',
                f'export OBJECT_STORAGE_BUCKET="{data.bucket.bucket_name}"',
                f'export AWS_REGION="{self.region}"',
                'export SSM_PREFIX="/lectify/"',
                f'export ALB_ORIGIN="http://{alb_dns}"',
            ])

            if tier == "web":
                cmds.append("bash /opt/lectify/bootstrap/api.sh")
            else:
                cmds.append("bash /opt/lectify/bootstrap/worker.sh")

            return cmds

        for cmd in _build_commands("web"):
            self.web_user_data.add_commands(cmd)
        self.web_user_data.add_signal_on_exit_command(self.web_asg)

        for cmd in _build_commands("worker"):
            self.worker_user_data.add_commands(cmd)
        self.worker_user_data.add_signal_on_exit_command(self.worker_asg)
