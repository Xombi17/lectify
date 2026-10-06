from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_kms as kms
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_sqs as sqs
from constructs import Construct

STAGES = ("transcribe", "materials", "embed")


class DataStack(Stack):
    """S3 storage, SQS stage queues + shared DLQ, SNS lecture-ready topic."""

    def __init__(self, scope: Construct, cid: str, *, network, app_origin: str, ready_emails: list[str],
                 recording_expiry_days: int = 30, **kw):
        super().__init__(scope, cid, **kw)

        self.bucket = s3.Bucket(
            self, "Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[s3.CorsRule(
                allowed_origins=[app_origin],
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.POST, s3.HttpMethods.HEAD],
                allowed_headers=["*"],
                exposed_headers=["ETag"],
                max_age=3000,
            )],
            lifecycle_rules=[
                s3.LifecycleRule(id="AbortIncompleteMultipart", abort_incomplete_multipart_upload_after=Duration.days(1)),
                s3.LifecycleRule(id="ExpireRecordings", prefix="classes/", expiration=Duration.days(recording_expiry_days)),
            ],
        )

        self.dlq = sqs.Queue(
            self, "Dlq", queue_name="lectify-dlq",
            encryption=sqs.QueueEncryption.SQS_MANAGED, enforce_ssl=True,
            retention_period=Duration.days(14), receive_message_wait_time=Duration.seconds(20),
        )
        self.queues = {
            s: sqs.Queue(
                self, f"Q-{s}", queue_name=f"lectify-{s}",
                encryption=sqs.QueueEncryption.SQS_MANAGED, enforce_ssl=True,
                visibility_timeout=Duration.seconds(900), retention_period=Duration.days(4),
                receive_message_wait_time=Duration.seconds(20),
                dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=5, queue=self.dlq),
            )
            for s in STAGES
        }

        self.topic = sns.Topic(
            self, "ReadyTopic", topic_name="lectify-lecture-ready",
            master_key=kms.Alias.from_alias_name(self, "SnsKey", "alias/aws/sns"),
            enforce_ssl=True,
        )
        for e in ready_emails:
            self.topic.add_subscription(subs.EmailSubscription(e))

        engine = rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16_13)
        self.parameter_group = rds.ParameterGroup(self, "RdsParameterGroup", engine=engine, parameters={"rds.force_ssl": "1"})
        self.credentials = rds.Credentials.from_generated_secret("lectify", secret_name="lectify/rds/credentials")
        self.db = rds.DatabaseInstance(
            self, "Db", engine=engine, parameter_group=self.parameter_group, credentials=self.credentials,
            instance_type=ec2.InstanceType("t4g.micro"), multi_az=False,
            allocated_storage=20, storage_type=rds.StorageType.GP3, storage_encrypted=True,
            vpc=network.vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[network.sg_rds], publicly_accessible=False,
            backup_retention=Duration.days(1), deletion_protection=False,
            delete_automated_backups=True, removal_policy=RemovalPolicy.DESTROY,
        )

        for k, v in {
            "BucketName": self.bucket.bucket_name,
            "TranscribeQueueUrl": self.queues["transcribe"].queue_url,
            "MaterialsQueueUrl": self.queues["materials"].queue_url,
            "EmbedQueueUrl": self.queues["embed"].queue_url,
            "DlqUrl": self.dlq.queue_url,
            "LectureReadyTopicArn": self.topic.topic_arn,
            "RdsEndpoint": self.db.db_instance_endpoint_address,
            "RdsPort": self.db.db_instance_endpoint_port,
            "RdsSecretArn": self.db.secret.secret_arn,
            "SsmPrefix": "/lectify/",
        }.items():
            CfnOutput(self, k, value=v)
