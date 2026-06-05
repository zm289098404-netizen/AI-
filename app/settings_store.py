"""运行时应用配置：管理员可在管理端切换 AI 模型（Chat / Embedding）等。

生效值优先级：数据库覆盖值 > .env 默认值。
存储于 app_settings 表（key-value）。
"""
import time
import sqlite3
from typing import Optional

from app.config import settings
from app.db import get_conn, init_all

# 可切换项的键名
KEY_CHAT = "chat_deployment"
KEY_EMBED = "embedding_deployment"
KEY_TEMPERATURE = "temperature"
KEY_MOCK_MODE = "mock_mode"  # auto | on | off
KEY_PROVIDER = "ai_provider"
KEY_BASE_URL = "ai_base_url"
KEY_API_KEY = "ai_api_key"
KEY_AZURE_ENDPOINT = "azure_endpoint"
KEY_API_VERSION = "api_version"

MOCK_MODES = ("auto", "on", "off")
PROVIDERS = (
    "azure_openai",
    "openai_compatible",
    "deepseek",
    "dashscope_qwen",
    "zhipu",
    "siliconflow",
    "moonshot",
)

PROVIDER_PRESETS = [
    {
        "id": "azure_openai",
        "name": "Azure OpenAI",
        "mode": "azure",
        "base_url": "",
        "chat": "gpt-4o",
        "embedding": "text-embedding-3-small",
        "note": "企业 Azure OpenAI 部署；需填写 Endpoint 与 API Key。",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek（OpenAI兼容）",
        "mode": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "chat": "deepseek-chat",
        "embedding": "",
        "note": "适合低成本中文生成；若无 embedding 服务，可继续使用 Mock/本地向量索引。",
    },
    {
        "id": "dashscope_qwen",
        "name": "通义千问 DashScope（OpenAI兼容）",
        "mode": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "chat": "qwen-plus",
        "embedding": "text-embedding-v3",
        "note": "阿里云百炼/通义千问兼容接口，通常有免费额度。",
    },
    {
        "id": "zhipu",
        "name": "智谱 GLM（OpenAI兼容）",
        "mode": "openai_compatible",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "chat": "glm-4-flash",
        "embedding": "embedding-3",
        "note": "智谱开放平台兼容接口，适合中文场景。",
    },
    {
        "id": "siliconflow",
        "name": "SiliconFlow（聚合/开源模型）",
        "mode": "openai_compatible",
        "base_url": "https://api.siliconflow.cn/v1",
        "chat": "Qwen/Qwen2.5-7B-Instruct",
        "embedding": "BAAI/bge-m3",
        "note": "支持多种国产/开源模型与 embedding，适合测试体验。",
    },
    {
        "id": "moonshot",
        "name": "Moonshot / Kimi（OpenAI兼容）",
        "mode": "openai_compatible",
        "base_url": "https://api.moonshot.cn/v1",
        "chat": "moonshot-v1-8k",
        "embedding": "",
        "note": "适合长文本生成；如无 embedding 服务，检索可保留已有索引。",
    },
    {
        "id": "openai_compatible",
        "name": "自定义 OpenAI 兼容服务",
        "mode": "openai_compatible",
        "base_url": "",
        "chat": "",
        "embedding": "",
        "note": "填写 Base URL、API Key、模型名即可接入兼容服务。",
    },
]

# UI 预设候选（管理端下拉），同时支持自定义输入
CHAT_PRESETS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4-turbo", "gpt-35-turbo"]
EMBED_PRESETS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]


def _get_raw(key: str) -> Optional[str]:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key=?", (key,)
            ).fetchone()
    except sqlite3.OperationalError:
        init_all()
        with get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key=?", (key,)
            ).fetchone()
    return row["value"] if row else None


def _set_raw(key: str, value: str) -> None:
    init_all()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_settings(key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, time.time()),
        )


# ---------------- 生效值 ----------------
def chat_deployment() -> str:
    return _get_raw(KEY_CHAT) or settings.azure_openai_chat_deployment


def embedding_deployment() -> str:
    return _get_raw(KEY_EMBED) or settings.azure_openai_embedding_deployment


def temperature() -> float:
    raw = _get_raw(KEY_TEMPERATURE)
    if raw is None:
        return 0.3
    try:
        return float(raw)
    except ValueError:
        return 0.3


def provider() -> str:
    raw = _get_raw(KEY_PROVIDER)
    return raw if raw in PROVIDERS else "azure_openai"


def provider_mode() -> str:
    p = provider()
    if p == "azure_openai":
        return "azure"
    return "openai_compatible"


def base_url() -> str:
    raw = _get_raw(KEY_BASE_URL)
    if raw:
        return raw
    preset = next((p for p in PROVIDER_PRESETS if p["id"] == provider()), None)
    return (preset or {}).get("base_url", "")


def api_key() -> str:
    raw = _get_raw(KEY_API_KEY)
    if raw:
        return raw
    return settings.azure_openai_api_key if provider_mode() == "azure" else ""


def azure_endpoint() -> str:
    return _get_raw(KEY_AZURE_ENDPOINT) or settings.azure_openai_endpoint


def api_version() -> str:
    return _get_raw(KEY_API_VERSION) or settings.azure_openai_api_version


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


# ---------------- Mock 模式 ----------------
def has_credentials() -> bool:
    """是否配置了当前 provider 所需凭据。"""
    if provider_mode() == "azure":
        return bool(azure_endpoint() and api_key())
    return bool(base_url() and api_key())


def mock_mode_setting() -> str:
    """管理员设置：auto / on / off（默认 auto）。"""
    raw = _get_raw(KEY_MOCK_MODE)
    return raw if raw in MOCK_MODES else "auto"


def effective_mock() -> bool:
    """实际是否处于 Mock 模式。

    - on  : 强制 Mock
    - off : 强制真实（仅在有凭据时有效；无凭据则仍回退 Mock）
    - auto: 依据是否有凭据自动判定
    """
    mode = mock_mode_setting()
    if mode == "on":
        return True
    if mode == "off":
        return not has_credentials()  # 无凭据时无法真正关闭
    return not has_credentials()


# ---------------- 管理端读写 ----------------
def get_model_config() -> dict:
    """返回当前生效配置 + 默认值 + 是否被覆盖 + 运行模式。"""
    eff_mock = effective_mock()
    key = api_key()
    return {
        "provider": provider(),
        "provider_mode": provider_mode(),
        "provider_presets": PROVIDER_PRESETS,
        "base_url": base_url(),
        "azure_endpoint": azure_endpoint(),
        "api_version": api_version(),
        "api_key_set": bool(key),
        "api_key_masked": _mask_secret(key),
        "chat_deployment": chat_deployment(),
        "embedding_deployment": embedding_deployment(),
        "temperature": temperature(),
        "chat_default": settings.azure_openai_chat_deployment,
        "embedding_default": settings.azure_openai_embedding_deployment,
        "provider_overridden": _get_raw(KEY_PROVIDER) is not None,
        "base_url_overridden": _get_raw(KEY_BASE_URL) is not None,
        "azure_endpoint_overridden": _get_raw(KEY_AZURE_ENDPOINT) is not None,
        "api_key_overridden": _get_raw(KEY_API_KEY) is not None,
        "chat_overridden": _get_raw(KEY_CHAT) is not None,
        "embedding_overridden": _get_raw(KEY_EMBED) is not None,
        "temperature_overridden": _get_raw(KEY_TEMPERATURE) is not None,
        "chat_presets": CHAT_PRESETS,
        "embedding_presets": EMBED_PRESETS,
        "mock_mode_setting": mock_mode_setting(),
        "mock_mode": eff_mock,
        "has_credentials": has_credentials(),
        "backend": "azure_search" if settings.use_azure_search else "chromadb",
    }


def update_model_config(
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    azure_endpoint: Optional[str] = None,
    api_version: Optional[str] = None,
    chat_deployment: Optional[str] = None,
    embedding_deployment: Optional[str] = None,
    temperature: Optional[float] = None,
    mock_mode: Optional[str] = None,
    clear_api_key: bool = False,
    reset: bool = False,
) -> dict:
    """更新运行时模型配置。reset=True 则清除覆盖、回退到 .env 默认。"""
    if reset:
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM app_settings WHERE key IN (?,?,?,?,?,?,?,?,?)",
                (
                    KEY_CHAT,
                    KEY_EMBED,
                    KEY_TEMPERATURE,
                    KEY_MOCK_MODE,
                    KEY_PROVIDER,
                    KEY_BASE_URL,
                    KEY_API_KEY,
                    KEY_AZURE_ENDPOINT,
                    KEY_API_VERSION,
                ),
            )
        _notify_change()
        return get_model_config()

    if provider is not None and provider.strip():
        p = provider.strip()
        if p not in PROVIDERS:
            from fastapi import HTTPException

            raise HTTPException(400, f"provider 仅支持 {PROVIDERS}")
        _set_raw(KEY_PROVIDER, p)
        preset = next((x for x in PROVIDER_PRESETS if x["id"] == p), None)
        # 切换预设时自动带入默认 URL/模型（用户后续可覆盖）
        if preset:
            if preset.get("base_url"):
                _set_raw(KEY_BASE_URL, preset["base_url"])
            if preset.get("chat"):
                _set_raw(KEY_CHAT, preset["chat"])
            if preset.get("embedding"):
                _set_raw(KEY_EMBED, preset["embedding"])
    if base_url is not None and base_url.strip():
        _set_raw(KEY_BASE_URL, base_url.strip())
    if azure_endpoint is not None and azure_endpoint.strip():
        _set_raw(KEY_AZURE_ENDPOINT, azure_endpoint.strip())
    if api_version is not None and api_version.strip():
        _set_raw(KEY_API_VERSION, api_version.strip())
    if clear_api_key:
        with get_conn() as conn:
            conn.execute("DELETE FROM app_settings WHERE key=?", (KEY_API_KEY,))
    elif api_key is not None and api_key.strip():
        _set_raw(KEY_API_KEY, api_key.strip())
    if chat_deployment is not None and chat_deployment.strip():
        _set_raw(KEY_CHAT, chat_deployment.strip())
    if embedding_deployment is not None and embedding_deployment.strip():
        _set_raw(KEY_EMBED, embedding_deployment.strip())
    if temperature is not None:
        t = max(0.0, min(2.0, float(temperature)))
        _set_raw(KEY_TEMPERATURE, str(t))
    if mock_mode is not None:
        mode = mock_mode.strip().lower()
        if mode not in MOCK_MODES:
            from fastapi import HTTPException

            raise HTTPException(400, f"mock_mode 仅支持 {MOCK_MODES}")
        _set_raw(KEY_MOCK_MODE, mode)

    _notify_change()
    return get_model_config()


def _notify_change() -> None:
    """配置变更后重置 LLM 客户端缓存，使 Mock/真实切换即时生效。"""
    try:
        from app.rag.azure_client import reset_llm

        reset_llm()
    except Exception:
        pass
