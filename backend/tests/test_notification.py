import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models.job import JobDB
from workers.ai import AIWorker
from services.notification_service import publish_lecture_ready
from core.config import get_settings

@pytest.mark.asyncio
async def test_publish_lecture_ready_unset_arn():
    """unset ARN -> returns False, fake client never created"""
    mock_settings = MagicMock()
    mock_settings.LECTURE_READY_TOPIC_ARN = ""
    
    with patch("services.notification_service.get_settings", return_value=mock_settings), \
         patch("aioboto3.Session") as mock_session:
        result = await publish_lecture_ready("l1", "c1")
        
    assert result is False
    mock_session.assert_not_called()

@pytest.mark.asyncio
async def test_publish_lecture_ready_success():
    """fake SNS client records publish"""
    mock_settings = MagicMock()
    mock_settings.LECTURE_READY_TOPIC_ARN = "arn:aws:sns:test"
    mock_settings.AWS_REGION = "us-east-1"
    
    mock_publish = AsyncMock()
    mock_client = AsyncMock()
    mock_client.publish = mock_publish
    
    class MockClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    mock_session = MagicMock()
    mock_session.client.return_value = MockClientContext()
    
    with patch("services.notification_service.get_settings", return_value=mock_settings), \
         patch("services.notification_service.aioboto3.Session", return_value=mock_session):
        result = await publish_lecture_ready("lec123", "class456")
        
    assert result is True
    mock_publish.assert_called_once()
    kwargs = mock_publish.call_args.kwargs
    assert kwargs["TopicArn"] == "arn:aws:sns:test"
    assert json.loads(kwargs["Message"]) == {"status": "ready"}
    assert kwargs["MessageAttributes"]["lecture_id"]["StringValue"] == "lec123"
    assert kwargs["MessageAttributes"]["class_id"]["StringValue"] == "class456"

@pytest.mark.asyncio
async def test_publish_lecture_ready_no_class():
    """class_id attribute is empty string when no class"""
    mock_settings = MagicMock()
    mock_settings.LECTURE_READY_TOPIC_ARN = "arn:aws:sns:test"
    mock_settings.AWS_REGION = "us-east-1"
    
    mock_publish = AsyncMock()
    mock_client = AsyncMock()
    mock_client.publish = mock_publish
    
    class MockClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    mock_session = MagicMock()
    mock_session.client.return_value = MockClientContext()
    
    with patch("services.notification_service.get_settings", return_value=mock_settings), \
         patch("services.notification_service.aioboto3.Session", return_value=mock_session):
        result = await publish_lecture_ready("lec123", None)
        
    assert result is True
    kwargs = mock_publish.call_args.kwargs
    assert kwargs["MessageAttributes"]["class_id"]["StringValue"] == ""

@pytest.mark.asyncio
async def test_publish_lecture_ready_raises(caplog):
    """fake client raising -> returns False, logs WARNING"""
    mock_settings = MagicMock()
    mock_settings.LECTURE_READY_TOPIC_ARN = "arn:aws:sns:test"
    mock_settings.AWS_REGION = "us-east-1"
    
    mock_publish = AsyncMock(side_effect=RuntimeError("SNS down"))
    mock_client = AsyncMock()
    mock_client.publish = mock_publish
    
    class MockClientContext:
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    mock_session = MagicMock()
    mock_session.client.return_value = MockClientContext()
    
    with patch("services.notification_service.get_settings", return_value=mock_settings), \
         patch("services.notification_service.aioboto3.Session", return_value=mock_session):
        result = await publish_lecture_ready("lec123", "class456")
        
    assert result is False
    assert "Failed to publish lecture ready notification for lec123" in caplog.text

@pytest.mark.asyncio
async def test_ai_worker_notification_hook(monkeypatch):
    """AI worker pipeline calls publish_lecture_ready after status=ready update"""
    # Create an AIWorker and process a job
    worker = AIWorker(max_jobs=1)
    
    from models.job import JobDB
    from workers.base import JobContext
    from services.ai_service import AIProvider
    from repositories.lecture_repository import LectureRepository
    
    # Mock AI Service
    ai_mock = AsyncMock(spec=AIProvider)
    ai_mock.generate_study_materials.return_value = MagicMock(summary="s", key_concepts=["k"], quiz=[], flashcards=[])
    ai_mock.embed.return_value = [0.1]
    
    # Mock Repo
    class MockRepo:
        def __init__(self):
            self.calls = []
        async def get_by_id(self, lid):
            lecture = MagicMock()
            lecture.transcript = "dummy"
            lecture.duration_seconds = 10
            lecture.class_id = "c1"
            return lecture
        async def update_fields(self, lid, fields):
            self.calls.append(("update", fields))
            
    repo = MockRepo()
    
    mock_publish = AsyncMock()
    
    with patch("workers.ai.get_ai_service", return_value=ai_mock), \
         patch("workers.ai.LectureRepository", return_value=repo), \
         patch("workers.ai.publish_lecture_ready", new=mock_publish), \
         patch("workers.ai._extract_and_store_knowledge_graph", new=AsyncMock()):
        
        job = JobDB(id="j1", lecture_id="l1", stage="generate_materials", version=1, status="processing")
        ctx = AsyncMock(spec=JobContext)
        await worker.process_job(job, ctx)
        
    mock_publish.assert_called_once_with("l1", "c1")
    
    # Check it was called AFTER the 'ready' update
    # The last update call should set status='ready'
    last_update = repo.calls[-1]
    assert last_update[0] == "update"
    assert last_update[1].get("status") == "ready"
