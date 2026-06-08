"""Dispatches to the SQL InstitutionRepository implementation."""
from repositories._sql.academic_repository import InstitutionRepository  # noqa: F401

__all__ = ["InstitutionRepository"]
