"""章节模板模块单元测试。"""
import pytest
from fastapi import HTTPException

from app import auth, templates_store


@pytest.fixture(autouse=True, scope="module")
def _init():
    auth.init_db()


def test_builtin_templates_listed():
    items = templates_store.list_templates("demo")
    names = [t["name"] for t in items]
    assert "标准投标方案" in names
    assert all(t["builtin"] for t in items if t["name"] in templates_store.BUILTIN_TEMPLATES)


def test_resolve_builtin_sections():
    secs = templates_store.resolve_sections("demo", "builtin:POC/试点方案")
    assert "验收标准与成功指标" in secs


def test_resolve_none_returns_none():
    assert templates_store.resolve_sections("demo", None) is None


def test_create_and_resolve_custom_template():
    t = templates_store.create_template("demo", "单测模板", ["章节A", "章节B"])
    assert t["builtin"] is False
    secs = templates_store.resolve_sections("demo", t["id"])
    assert secs == ["章节A", "章节B"]


def test_custom_template_tenant_isolation():
    t = templates_store.create_template("tenantX", "X专属", ["X1"])
    # 其他租户看不到，且无法解析
    names_other = [x["name"] for x in templates_store.list_templates("tenantY")]
    assert "X专属" not in names_other
    with pytest.raises(HTTPException):
        templates_store.resolve_sections("tenantY", t["id"])


def test_create_empty_sections_rejected():
    with pytest.raises(HTTPException) as ei:
        templates_store.create_template("demo", "空模板", [])
    assert ei.value.status_code == 400


def test_cannot_conflict_builtin_name():
    with pytest.raises(HTTPException) as ei:
        templates_store.create_template("demo", "标准投标方案", ["x"])
    assert ei.value.status_code == 409


def test_delete_builtin_rejected():
    with pytest.raises(HTTPException) as ei:
        templates_store.delete_template("demo", "builtin:标准投标方案")
    assert ei.value.status_code == 400


def test_delete_custom_template():
    t = templates_store.create_template("demo", "待删除", ["a"])
    templates_store.delete_template("demo", t["id"])
    with pytest.raises(HTTPException):
        templates_store.resolve_sections("demo", t["id"])
