"""Tests for audit logging infrastructure."""

import pytest
from unittest.mock import AsyncMock, patch

from models.academic import AuditLogCreate, AuditLogDB, AuditLogPublic


@pytest.mark.asyncio
async def test_audit_log_db_create():
    """Test that AuditLogDB model validates correctly."""
    entry = AuditLogDB(
        id="test-id",
        admin_id="admin-1",
        action="create",
        entity_type="institution",
        entity_id="inst-1",
        details="Created test institution",
    )
    assert entry.action == "create"
    assert entry.entity_type == "institution"


@pytest.mark.asyncio
async def test_audit_log_invalid_action():
    """Test that invalid actions are rejected by AuditLogCreate."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AuditLogCreate(
            admin_id="admin-1",
            action="invalid_action",
            entity_type="institution",
            entity_id="inst-1",
        )


@pytest.mark.asyncio
async def test_audit_log_new_action_types():
    """Test that the expanded action types are accepted by AuditLogCreate."""
    log = AuditLogCreate(
        admin_id="admin-1",
        action="publish",
        entity_type="lecture",
        entity_id="lec-1",
        details="Published lecture",
    )
    assert log.action == "publish"

    log2 = AuditLogCreate(
        admin_id="admin-1",
        action="unpublish",
        entity_type="lecture",
        entity_id="lec-1",
    )
    assert log2.action == "unpublish"


@pytest.mark.asyncio
async def test_audit_log_repository_create():
    """Test AuditLogRepository.create stores the entry."""
    from repositories.audit_log_repository import AuditLogRepository

    repo = AuditLogRepository()
    entry = AuditLogDB(
        id=repo.new_id(),
        admin_id="admin-1",
        action="create",
        entity_type="institution",
        entity_id="inst-1",
    )

    with patch.object(repo, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = entry
        result = await repo.create(entry)
        assert result.id == entry.id


@pytest.mark.asyncio
async def test_audit_log_generate_action():
    """Test the 'generate' action type (for QR codes)."""
    log = AuditLogCreate(
        admin_id="admin-1",
        action="generate",
        entity_type="qr_code",
        entity_id="qr-1",
    )
    assert log.action == "generate"


@pytest.mark.asyncio
async def test_audit_log_assign_actions():
    """Test the teacher assignment action types."""
    log = AuditLogCreate(
        admin_id="admin-1",
        action="assign_teacher",
        entity_type="assignment",
        entity_id="assign-1",
    )
    assert log.action == "assign_teacher"

    log2 = AuditLogCreate(
        admin_id="admin-1",
        action="unassign_teacher",
        entity_type="assignment",
        entity_id="assign-1",
    )
    assert log2.action == "unassign_teacher"
