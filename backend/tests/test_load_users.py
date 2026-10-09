"""Tests for load-test user seeding and token minting."""
from unittest.mock import patch

import pytest

from core.security import decode_access_token
from core.sql_db import session_maker
from scripts import load_users
from scripts.load_users import load_email, load_user_id, mint_tokens, seed_load_users
from scripts.seed_demo import _deterministic_id, seed

PW = {"admin": "AdminPassword123!", "teacher": "TeacherPassword123!", "student": "StudentPassword123!"}


def test_ids_deterministic():
    assert load_email(7) == "load0007@demo.lectify"
    assert load_user_id(7) == _deterministic_id("user.load0007@demo.lectify")


def test_mint_tokens_decodable():
    tokens = mint_tokens(3)
    assert len(tokens) == 3
    for i, t in enumerate(tokens):
        d = decode_access_token(t)
        assert d["sub"] == load_user_id(i) and d["role"] == "student"


@pytest.mark.asyncio
async def test_seed_requires_demo_class():
    async with session_maker()() as s:
        with pytest.raises(RuntimeError, match="seed_demo"):
            await seed_load_users(s, 2, "x" * 12)


@pytest.mark.asyncio
async def test_seed_idempotent_single_hash():
    maker = session_maker()
    async with maker() as s:
        await seed(s, PW)
    with patch.object(load_users, "hash_password", wraps=load_users.hash_password) as hp:
        async with maker() as s:
            c1 = await seed_load_users(s, 5, "x" * 12)
        assert hp.call_count == 1
    assert c1["users"] == 5 and c1["enrollments"] == 5
    async with maker() as s:
        c2 = await seed_load_users(s, 5, "x" * 12)
    assert c2["created"] == 0
