import json
import logging

import aioboto3
from core.config import get_settings

logger = logging.getLogger(__name__)


async def publish_lecture_ready(lecture_id: str, class_id: str | None) -> bool:
    """Publish a best-effort SNS notification that a lecture is ready."""
    settings = get_settings()
    topic_arn = settings.LECTURE_READY_TOPIC_ARN

    if not topic_arn:
        return False

    try:
        session = aioboto3.Session()
        async with session.client("sns", region_name=settings.AWS_REGION) as sns_client:
            await sns_client.publish(
                TopicArn=topic_arn,
                Message=json.dumps({"status": "ready"}),
                MessageAttributes={
                    "class_id": {
                        "DataType": "String",
                        "StringValue": class_id if class_id is not None else "",
                    },
                    "lecture_id": {"DataType": "String", "StringValue": lecture_id},
                },
            )
        return True
    except Exception:
        logger.warning(
            "Failed to publish lecture ready notification for %s",
            lecture_id,
            exc_info=False,
        )
        return False
