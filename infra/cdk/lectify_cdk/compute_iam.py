"""Least-privilege IAM roles for the API and worker compute tiers."""
from typing import Sequence
from aws_cdk import ArnFormat, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct

LOG_GROUP_API = "/lectify/api"
LOG_GROUP_WEB = "/lectify/web"
LOG_GROUP_WORKER = "/lectify/worker"


def _add_log_write(role: iam.Role, stack: Stack, names: Sequence[str]) -> None:
    """Write-only access to fixed log groups (CDK owns creation/retention)."""
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
            ],
            resources=[
                stack.format_arn(
                    service="logs",
                    resource="log-group",
                    resource_name=f"{n}:*",
                    arn_format=ArnFormat.COLON_RESOURCE_NAME,
                )
                for n in names
            ],
        )
    )


def build_api_role(
    scope: Construct,
    data,
    extra_read_arns: Sequence[str] | None = None,
) -> iam.Role:
    """Build the least-privilege IAM role for API instances."""
    role = iam.Role(
        scope,
        "ApiRole",
        assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        ],
    )

    stack = Stack.of(scope)
    ssm_wildcard_arn = stack.format_arn(
        service="ssm",
        resource="parameter",
        resource_name="lectify/*",
        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
    )
    ssm_root_arn = stack.format_arn(
        service="ssm",
        resource="parameter",
        resource_name="lectify",
        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
    )

    # 1. S3 class objects: Get, Put, Abort
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "s3:PutObject",
                "s3:GetObject",
                "s3:AbortMultipartUpload",
            ],
            resources=[data.bucket.arn_for_objects("classes/*")],
        )
    )

    # 2. SQS: Send message to stage queues only
    stage_queue_arns = [q.queue_arn for q in data.queues.values()]
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["sqs:SendMessage"],
            resources=stage_queue_arns,
        )
    )

    # 3. SSM parameter store: /lectify/*
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath",
            ],
            resources=[ssm_wildcard_arn, ssm_root_arn],
        )
    )

    # 4. Secrets Manager: RDS DB credentials only
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[data.db.secret.secret_arn],
        )
    )

    _add_log_write(role, stack, (LOG_GROUP_API, LOG_GROUP_WEB))

    # Optional asset read permissions (for CDK deployment assets in 15-05)
    if extra_read_arns:
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=list(extra_read_arns),
            )
        )

    return role


def build_worker_role(
    scope: Construct,
    data,
    extra_read_arns: Sequence[str] | None = None,
) -> iam.Role:
    """Build the least-privilege IAM role for background worker instances."""
    role = iam.Role(
        scope,
        "WorkerRole",
        assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        ],
    )

    stack = Stack.of(scope)
    ssm_wildcard_arn = stack.format_arn(
        service="ssm",
        resource="parameter",
        resource_name="lectify/*",
        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
    )
    ssm_root_arn = stack.format_arn(
        service="ssm",
        resource="parameter",
        resource_name="lectify",
        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
    )

    # 1. S3 class objects: Get, Put
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject"],
            resources=[data.bucket.arn_for_objects("classes/*")],
        )
    )

    # 2. S3 ListBucket: classes/* prefix only
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["s3:ListBucket"],
            resources=[data.bucket.bucket_arn],
            conditions={"StringLike": {"s3:prefix": ["classes/*"]}},
        )
    )

    # 3. SQS: Full consumer + producer on stage queues (DLQ redrive excluded)
    stage_queue_arns = [q.queue_arn for q in data.queues.values()]
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:ChangeMessageVisibility",
                "sqs:GetQueueAttributes",
                "sqs:SendMessage",
            ],
            resources=stage_queue_arns,
        )
    )

    # 4. SNS: Publish lecture-ready notifications
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["sns:Publish"],
            resources=[data.topic.topic_arn],
        )
    )

    # 5. SSM parameter store: /lectify/*
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath",
            ],
            resources=[ssm_wildcard_arn, ssm_root_arn],
        )
    )

    # 6. Secrets Manager: RDS DB credentials only
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[data.db.secret.secret_arn],
        )
    )

    _add_log_write(role, stack, (LOG_GROUP_WORKER,))

    # Optional asset read permissions (for CDK deployment assets in 15-05)
    if extra_read_arns:
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=list(extra_read_arns),
            )
        )

    return role
