"""AI 模型配置（settings_store）单元测试。"""
import pytest

from app import auth, settings_store
from app.config import settings


@pytest.fixture(autouse=True, scope="module")
def _init():
    auth.init_db()


@pytest.fixture(autouse=True)
def _clean():
    # 每个用例前后清除覆盖，保证隔离
    settings_store.update_model_config(reset=True)
    yield
    settings_store.update_model_config(reset=True)


def test_defaults_fall_back_to_env():
    assert settings_store.chat_deployment() == settings.azure_openai_chat_deployment
    assert settings_store.embedding_deployment() == settings.azure_openai_embedding_deployment
    assert settings_store.temperature() == 0.3


def test_update_chat_deployment_persists():
    settings_store.update_model_config(chat_deployment="gpt-4o-mini")
    assert settings_store.chat_deployment() == "gpt-4o-mini"
    cfg = settings_store.get_model_config()
    assert cfg["chat_overridden"] is True
    assert cfg["chat_deployment"] == "gpt-4o-mini"


def test_update_embedding_and_temperature():
    settings_store.update_model_config(
        embedding_deployment="text-embedding-3-large", temperature=0.9
    )
    assert settings_store.embedding_deployment() == "text-embedding-3-large"
    assert settings_store.temperature() == 0.9


def test_temperature_clamped():
    settings_store.update_model_config(temperature=5.0)
    assert settings_store.temperature() == 2.0
    settings_store.update_model_config(temperature=-1.0)
    assert settings_store.temperature() == 0.0


def test_reset_restores_defaults():
    settings_store.update_model_config(chat_deployment="gpt-4-turbo", temperature=1.5)
    settings_store.update_model_config(reset=True)
    cfg = settings_store.get_model_config()
    assert cfg["chat_overridden"] is False
    assert cfg["temperature_overridden"] is False
    assert cfg["chat_deployment"] == settings.azure_openai_chat_deployment


def test_presets_present():
    cfg = settings_store.get_model_config()
    assert "gpt-4o" in cfg["chat_presets"]
    assert "text-embedding-3-small" in cfg["embedding_presets"]


def test_empty_values_ignored():
    settings_store.update_model_config(chat_deployment="gpt-4o")
    # 传空白不应覆盖已有值
    settings_store.update_model_config(chat_deployment="   ")
    assert settings_store.chat_deployment() == "gpt-4o"


# ---------------- Mock 模式切换 ----------------
def test_mock_setting_default_auto():
    cfg = settings_store.get_model_config()
    assert cfg["mock_mode_setting"] == "auto"
    # 测试环境无凭据 -> 自动为 Mock
    assert settings_store.effective_mock() is True
    assert cfg["has_credentials"] is False


def test_force_mock_on():
    settings_store.update_model_config(mock_mode="on")
    assert settings_store.mock_mode_setting() == "on"
    assert settings_store.effective_mock() is True


def test_force_mock_off_without_credentials_falls_back():
    # 无凭据时强制 off 仍应回退 Mock（不会真正调用 Azure）
    settings_store.update_model_config(mock_mode="off")
    assert settings_store.mock_mode_setting() == "off"
    assert settings_store.effective_mock() is True


def test_invalid_mock_mode_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        settings_store.update_model_config(mock_mode="invalid")
    assert ei.value.status_code == 400


def test_reset_clears_mock_setting():
    settings_store.update_model_config(mock_mode="on")
    settings_store.update_model_config(reset=True)
    assert settings_store.mock_mode_setting() == "auto"


# ---------------- Provider / API Key ----------------
def test_provider_presets_include_domestic_models():
    cfg = settings_store.get_model_config()
    ids = {p["id"] for p in cfg["provider_presets"]}
    assert {"deepseek", "dashscope_qwen", "zhipu", "siliconflow", "moonshot"}.issubset(ids)


def test_switch_provider_sets_defaults():
    settings_store.update_model_config(provider="deepseek")
    cfg = settings_store.get_model_config()
    assert cfg["provider"] == "deepseek"
    assert cfg["provider_mode"] == "openai_compatible"
    assert cfg["base_url"] == "https://api.deepseek.com/v1"
    assert cfg["chat_deployment"] == "deepseek-chat"


def test_api_key_is_masked_and_not_returned_plaintext():
    settings_store.update_model_config(provider="siliconflow", api_key="sk-test-1234567890")
    cfg = settings_store.get_model_config()
    assert cfg["api_key_set"] is True
    assert cfg["api_key_masked"].startswith("sk-t")
    assert "1234567890" not in cfg["api_key_masked"]


def test_force_real_with_openai_compatible_credentials():
    settings_store.update_model_config(
        provider="openai_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key",
        chat_deployment="my-chat",
        mock_mode="off",
    )
    assert settings_store.has_credentials() is True
    assert settings_store.effective_mock() is False


def test_clear_api_key_restores_no_credentials():
    settings_store.update_model_config(provider="deepseek", api_key="secret-key")
    assert settings_store.has_credentials() is True
    settings_store.update_model_config(clear_api_key=True)
    assert settings_store.has_credentials() is False


# ---------------- 部署模式 / 品牌 / 连接测试 ----------------
def test_deployment_mode_default_demo():
    s = settings_store.get_system_settings()
    assert s["deployment_mode"] == "demo"
    assert s["brand_name"] == settings_store.DEFAULT_BRAND_NAME


def test_set_deployment_mode_production_and_back():
    settings_store.set_deployment_mode("production")
    assert settings_store.deployment_mode() == "production"
    settings_store.set_deployment_mode("demo")
    assert settings_store.deployment_mode() == "demo"


def test_invalid_deployment_mode_rejected():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        settings_store.set_deployment_mode("staging")
    assert ei.value.status_code == 400


def test_brand_name_update_and_empty_rejected():
    from fastapi import HTTPException

    settings_store.set_brand_name("ABC 投标系统")
    assert settings_store.brand_name() == "ABC 投标系统"
    with pytest.raises(HTTPException):
        settings_store.set_brand_name("   ")
    # 恢复默认
    settings_store.set_brand_name(settings_store.DEFAULT_BRAND_NAME)


def test_test_connection_returns_mock_when_mocked():
    settings_store.update_model_config(mock_mode="on")
    r = settings_store.test_connection()
    assert r["ok"] is False
    assert r["mode"] == "mock"
    assert "Mock" in r["message"]
