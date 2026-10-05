import json
import logging
from core.config import get_settings
import aioboto3

logger = logging.getLogger(__name__)

_sns_client = None
_session = None

async def _get_sns_client():
    global _sns_client, _session
    if _sns_client is None:
        if _session is None:
            _session = aioboto3.Session()
        # The region should come from settings
        region = get_settings().AWS_REGION
        # Need to return an async context manager or handle client properly.
        # It's better to instantiate it once if possible, or just open and return.
        # Actually in aioboto3, you usually do `async with session.client(...)` 
        # For simplicity, we can do it inside the function or manage a global context.
    return _session.client("sns", region_name=get_settings().AWS_REGION)

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
                        "StringValue": class_id if class_id is not None else ""
                    },
                    "lecture_id": {
                        "DataType": "String",
                        "StringValue": lecture_id
                    }
                }
            )
        return True
    except Exception:
        logger.warning("Failed to publish lecture ready notification for %s", lecture_id, exc_info=False)
        return False
