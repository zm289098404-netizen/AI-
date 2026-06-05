"""认证与多租户：用户/租户存储(SQLite)、bcrypt 口令、HMAC 签名令牌。"""
import base64
import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from typing import Optional

import bcrypt
from fastapi import Header, HTTPException

from app.config import settings
from app.db import get_conn, init_all


# ---------------- 数据库 ----------------
def _conn() -> sqlite3.Connection:
    return get_conn()


def init_db() -> None:
    init_all()


# ---------------- 租户 ----------------
def create_tenant(tenant_id: str, name: str) -> dict:
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO tenants(id, name, created_at) VALUES (?,?,?)",
                (tenant_id, name, time.time()),
            )
        except sqlite3.IntegrityError:
            conn.execute("UPDATE tenants SET name=? WHERE id=?", (name, tenant_id))
    return {"id": tenant_id, "name": name}


def list_tenants() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT id, name FROM tenants ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


# ---------------- 用户 ----------------
def create_user(username, password, tenant_id, role="user", display_name=None) -> dict:
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    uid = str(uuid.uuid4())
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users(id, username, password_hash, tenant_id, role, display_name, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (uid, username, pw_hash, tenant_id, role, display_name or username, time.time()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"用户名已存在: {username}")
    return {
        "id": uid,
        "username": username,
        "tenant_id": tenant_id,
        "role": role,
        "display_name": display_name or username,
    }


def get_user(username: str) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()


def verify_user(username: str, password: str) -> Optional[dict]:
    row = get_user(username)
    if not row:
        return None
    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "tenant_id": row["tenant_id"],
        "role": row["role"],
        "display_name": row["display_name"],
    }


# ---------------- 令牌 (HMAC 签名，无外部依赖) ----------------
def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def make_token(user: dict) -> str:
    payload = {
        "sub": user["username"],
        "uid": user["id"],
        "tenant_id": user["tenant_id"],
        "role": user["role"],
        "display_name": user.get("display_name", user["username"]),
        "exp": time.time() + settings.token_ttl_hours * 3600,
    }
    body = _b64u(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64u(sig)}"


def parse_token(token: str) -> dict:
    try:
        body, sig = token.split(".")
        expected = hmac.new(
            settings.auth_secret.encode(), body.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64u(expected), sig):
            raise ValueError("签名无效")
        payload = json.loads(_b64u_decode(body))
        if payload.get("exp", 0) < time.time():
            raise ValueError("令牌已过期")
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"无效令牌: {e}")


# ---------------- FastAPI 依赖 ----------------
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "缺少认证令牌")
    token = authorization.split(" ", 1)[1].strip()
    return parse_token(token)


def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    user = get_current_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


# ---------------- 初始化默认数据 ----------------
DEFAULT_USERS = [
    # username, password, tenant_id, role, display_name
    ("admin", "admin123", "demo", "admin", "系统管理员"),
    ("presales", "demo123", "demo", "user", "售前-张工"),
    ("acme", "acme123", "acme", "admin", "ACME 管理员"),
]

DEFAULT_TENANTS = [
    ("demo", "示例公司（演示）"),
    ("acme", "ACME 科技"),
]


def ensure_seed_accounts() -> None:
    init_db()
    for tid, name in DEFAULT_TENANTS:
        create_tenant(tid, name)
    for username, pw, tid, role, dn in DEFAULT_USERS:
        if not get_user(username):
            create_user(username, pw, tid, role=role, display_name=dn)
