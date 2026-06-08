"""Dispatches to the SQL QRCodeRepository implementation."""
from repositories._sql.academic_repository import QRCodeRepository  # noqa: F401

__all__ = ["QRCodeRepository"]
