"""Database URL composition from AWS Secrets Manager."""
import json
import os
import urllib.parse
from typing import Any, Optional


def apply_db_secret_overlay(client: Optional[Any] = None) -> bool:
    """Compose and overlay DATABASE_URL from AWS Secrets Manager if configured.

    Precedence:
    - If DATABASE_URL is already set in os.environ, do nothing and return False.
    - If DB_SECRET_ARN is unset/empty, do nothing and return False.
    - If DB_SECRET_ARN is set, fetch credentials from Secrets Manager, read DB_HOST
      (and optional DB_PORT, DATABASE_NAME) from os.environ, percent-encode user/pass,
      and set os.environ["DATABASE_URL"].

    Raises:
        RuntimeError: if retrieval, decoding, or composition fails (with sensitive data redacted).
    """
    if os.environ.get("DATABASE_URL"):
        return False

    arn = os.environ.get("DB_SECRET_ARN")
    if not arn:
        return False

    host = os.environ.get("DB_HOST")
    if not host:
        raise RuntimeError("DB secret overlay failed: DB_HOST environment variable is not set")

    if client is None:
        import boto3
        client = boto3.client("secretsmanager")

    try:
        resp = client.get_secret_value(SecretId=arn)
        secret_str = resp.get("SecretString")
        if not secret_str:
            raise ValueError("SecretString is empty or missing")
        secret_data = json.loads(secret_str)
        if "username" not in secret_data or "password" not in secret_data:
            raise KeyError("Secret must contain 'username' and 'password' keys")

        user = str(secret_data["username"])
        password = str(secret_data["password"])
    except Exception as e:
        err_msg = str(e)
        if "password" in locals() and password and password in err_msg:
            err_msg = err_msg.replace(password, "[REDACTED]")
        raise RuntimeError(f"DB secret overlay failed: {err_msg}") from None

    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DATABASE_NAME", "postgres")

    encoded_user = urllib.parse.quote(user, safe="")
    encoded_pass = urllib.parse.quote(password, safe="")

    os.environ["DATABASE_URL"] = (
        f"postgresql+asyncpg://{encoded_user}:{encoded_pass}@{host}:{port}/{name}?ssl=require"
    )
    return True
