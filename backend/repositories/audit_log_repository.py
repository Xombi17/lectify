"""Dispatches to the SQL AuditLogRepository implementation."""
from repositories._sql.academic_repository import AuditLogRepository  # noqa: F401

__all__ = ["AuditLogRepository"]
