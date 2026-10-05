import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template

from lectify_cdk.data_stack import DataStack
from lectify_cdk.network_stack import NetworkStack


@pytest.fixture(scope="module")
def t():
    app = cdk.App()
    env = cdk.Environment(account="123456789012", region="ap-southeast-2")
    net = NetworkStack(app, "N", env=env)
    s = DataStack(app, "D", network=net, app_origin="http://localhost:3000", ready_emails=["a@example.com", "b@example.com"],
                  env=cdk.Environment(account="123456789012", region="ap-southeast-2"))
    return Template.from_stack(s)


def _one(t, type_):
    r = t.find_resources(type_)
    assert len(r) == 1
    return next(iter(r.values()))


def test_s3_bucket(t):
    b = _one(t, "AWS::S3::Bucket")
    p = b["Properties"]
    assert p["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True, "BlockPublicPolicy": True, "IgnorePublicAcls": True, "RestrictPublicBuckets": True}
    assert p["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
    assert p["OwnershipControls"]["Rules"][0]["ObjectOwnership"] == "BucketOwnerEnforced"
    assert "VersioningConfiguration" not in p
    assert b["DeletionPolicy"] == "Delete"
    t.resource_count_is("Custom::S3AutoDeleteObjects", 1)
    assert "aws:SecureTransport" in str(t.find_resources("AWS::S3::BucketPolicy"))


def test_s3_cors_and_lifecycle(t):
    p = _one(t, "AWS::S3::Bucket")["Properties"]
    c = p["CorsConfiguration"]["CorsRules"]
    assert len(c) == 1
    assert c[0]["AllowedOrigins"] == ["http://localhost:3000"]
    assert sorted(c[0]["AllowedMethods"]) == ["GET", "HEAD", "POST"]
    assert c[0]["ExposedHeaders"] == ["ETag"] and c[0]["MaxAge"] == 3000
    rules = {r["Id"]: r for r in p["LifecycleConfiguration"]["Rules"]}
    assert len(rules) == 2
    assert rules["AbortIncompleteMultipart"]["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 1
    assert rules["ExpireRecordings"]["Prefix"] == "classes/" and rules["ExpireRecordings"]["ExpirationInDays"] == 30


def test_sqs_queues(t):
    qs = t.find_resources("AWS::SQS::Queue")
    assert len(qs) == 4
    dlq_id = next(k for k, v in qs.items() if "RedrivePolicy" not in v["Properties"])
    assert qs[dlq_id]["Properties"]["MessageRetentionPeriod"] == 14 * 86400
    stage = [v["Properties"] for k, v in qs.items() if k != dlq_id]
    assert len(stage) == 3
    for p in stage:
        assert p["VisibilityTimeout"] == 900 and p["MessageRetentionPeriod"] == 4 * 86400
        assert p["RedrivePolicy"]["maxReceiveCount"] == 5
        assert p["RedrivePolicy"]["deadLetterTargetArn"] == {"Fn::GetAtt": [dlq_id, "Arn"]}
    for p in [qs[dlq_id]["Properties"], *stage]:
        assert p["SqsManagedSseEnabled"] is True and p["ReceiveMessageWaitTimeSeconds"] == 20
    assert str(t.find_resources("AWS::SQS::QueuePolicy")).count("aws:SecureTransport") >= 4


def test_sns_topic(t):
    p = _one(t, "AWS::SNS::Topic")["Properties"]
    assert p["TopicName"] == "lectify-lecture-ready" and "alias/aws/sns" in str(p["KmsMasterKeyId"])
    s = t.find_resources("AWS::SNS::Subscription")
    assert sorted(v["Properties"]["Endpoint"] for v in s.values()) == ["a@example.com", "b@example.com"]
    assert all(v["Properties"]["Protocol"] == "email" for v in s.values())
    assert "aws:SecureTransport" in str(t.find_resources("AWS::SNS::TopicPolicy"))


def test_rds_parameter_group(t):
    p = _one(t, "AWS::RDS::DBParameterGroup")["Properties"]
    assert p["Parameters"]["rds.force_ssl"] == "1" and p["Family"] == "postgres16"
    sec = _one(t, "AWS::SecretsManager::Secret")["Properties"]
    assert sec["Name"] == "lectify/rds/credentials"
    assert '"username":"lectify"' in sec["GenerateSecretString"]["SecretStringTemplate"].replace(" ", "")


def test_rds_instance(t):
    r = _one(t, "AWS::RDS::DBInstance")
    p = r["Properties"]
    assert p["PubliclyAccessible"] is False and p["MultiAZ"] is False
    assert p["DBInstanceClass"] == "db.t4g.micro" and p["Engine"] == "postgres" and p["EngineVersion"].startswith("16")
    assert p["AllocatedStorage"] == "20" and p["StorageType"] == "gp3" and p["StorageEncrypted"] is True
    assert p["BackupRetentionPeriod"] == 1 and p["DeletionProtection"] is False and p["DeleteAutomatedBackups"] is True
    assert r["DeletionPolicy"] == "Delete"
    assert len(p["VPCSecurityGroups"]) == 1 and "DBSubnetGroupName" in p
    assert "DBParameterGroupName" in p


def test_data_outputs(t):
    keys = set(t.to_json()["Outputs"])
    want = {"BucketName", "TranscribeQueueUrl", "MaterialsQueueUrl", "EmbedQueueUrl", "DlqUrl",
            "LectureReadyTopicArn", "RdsEndpoint", "RdsPort", "RdsSecretArn", "SsmPrefix"}
    assert want <= keys
    assert t.to_json()["Outputs"]["SsmPrefix"]["Value"] == "/lectify/"
