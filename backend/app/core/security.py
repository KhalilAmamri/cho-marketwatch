import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.db.connection import get_connection


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_access_token(payload: dict, secret: str, expires_minutes: int = 480) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    body["exp"] = int(time.time()) + (expires_minutes * 60)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{body_b64}".encode("utf-8")

    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{body_b64}.{signature_b64}"


def decode_access_token(token: str, secret: str) -> dict | None:
    try:
        header_b64, body_b64, signature_b64 = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_b64}.{body_b64}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_signature, actual_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(body_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None

    return payload


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    return token


def get_token_payload(authorization: str | None = Header(default=None)) -> dict:
    token = extract_bearer_token(authorization)
    payload = decode_access_token(token, settings.AUTH_SECRET)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return payload


def get_current_user(payload: dict = Depends(get_token_payload)) -> dict:
    user_id = payload.get("uid")
    username = payload.get("sub")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is not None:
                cur.execute(
                    """
                    SELECT u.id, u.username, u.full_name, r.name AS role, u.is_active
                    FROM users u
                    JOIN roles r ON u.role_id = r.id
                    WHERE u.id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT u.id, u.username, u.full_name, r.name AS role, u.is_active
                    FROM users u
                    JOIN roles r ON u.role_id = r.id
                    WHERE u.username = %s
                    LIMIT 1
                    """,
                    (username,),
                )

            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    resolved_id, resolved_username, full_name, role, is_active = row
    if not is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    return {
        "id": resolved_id,
        "username": resolved_username,
        "full_name": full_name,
        "role": role,
    }


def require_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
