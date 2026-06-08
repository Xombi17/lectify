"""Dispatches to the SQL BranchRepository implementation."""
from repositories._sql.academic_repository import BranchRepository  # noqa: F401

__all__ = ["BranchRepository"]
