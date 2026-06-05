"""认证模块单元测试：bcrypt 口令、HMAC 令牌、用户/租户。"""
import time

import pytest
from fastapi import HTTPException

from app import auth


@pytest.fixture(autouse=True, scope="module")
def _init():
    auth.init_db()


def test_token_roundtrip():
    user = {"id": "u1", "username": "alice", "tenant_id": "demo", "role": "user", "display_name": "Alice"}
    token = auth.make_token(user)
    payload = auth.parse_token(token)
    assert payload["sub"] == "alice"
    assert payload["tenant_id"] == "demo"
    assert payload["role"] == "user"


def test_tampered_token_rejected():
    user = {"id": "u1", "username": "bob", "tenant_id": "demo", "role": "user"}
    token = auth.make_token(user)
    body, sig = token.split(".")
    tampered = body + "x." + sig
    with pytest.raises(HTTPException) as ei:
        auth.parse_token(tampered)
    assert ei.value.status_code == 401


def test_expired_token_rejected(monkeypatch):
    user = {"id": "u1", "username": "carol", "tenant_id": "demo", "role": "user"}
    token = auth.make_token(user)
    # 将当前时间快进到 TTL 之后
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 999999)
    with pytest.raises(HTTPException) as ei:
        auth.parse_token(token)
    assert ei.value.status_code == 401


def test_create_and_verify_user():
    uname = "unituser_" + str(int(time.time() * 1000))
    auth.create_user(uname, "s3cret", "demo", role="user", display_name="单测用户")
    ok = auth.verify_user(uname, "s3cret")
    assert ok is not None
    assert ok["username"] == uname
    assert ok["tenant_id"] == "demo"
    # 错误口令
    assert auth.verify_user(uname, "wrong") is None
    # 不存在用户
    assert auth.verify_user("no_such_user_xyz", "x") is None


def test_duplicate_user_conflict():
    uname = "dupuser_" + str(int(time.time() * 1000))
    auth.create_user(uname, "p", "demo")
    with pytest.raises(HTTPException) as ei:
        auth.create_user(uname, "p", "demo")
    assert ei.value.status_code == 409


def test_seed_accounts_idempotent():
    auth.ensure_seed_accounts()
    auth.ensure_seed_accounts()  # 第二次不应抛错
    assert auth.verify_user("admin", "admin123") is not None
