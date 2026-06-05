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
