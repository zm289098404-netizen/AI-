"""运行时应用配置：管理员可在管理端切换 AI 模型（Chat / Embedding）等。

生效值优先级：数据库覆盖值 > .env 默认值。
存储于 app_settings 表（key-value）。
"""
import time
from typing import Optional

from app.config import settings
from app.db import get_conn

# 可切换项的键名
KEY_CHAT = "chat_deployment"
KEY_EMBED = "embedding_deployment"
KEY_TEMPERATURE = "temperature"
KEY_MOCK_MODE = "mock_mode"  # auto | on | off

MOCK_MODES = ("auto", "on", "off")

# UI 预设候选（管理端下拉），同时支持自定义输入
CHAT_PRESETS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4-turbo", "gpt-35-turbo"]
EMBED_PRESETS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]


def _get_raw(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row else None


def _set_raw(key: str, value: str) -> None:
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


# ---------------- Mock 模式 ----------------
def has_credentials() -> bool:
    """是否配置了 Azure OpenAI 凭据。"""
    return bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)


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
    return {
        "chat_deployment": chat_deployment(),
        "embedding_deployment": embedding_deployment(),
        "temperature": temperature(),
        "chat_default": settings.azure_openai_chat_deployment,
        "embedding_default": settings.azure_openai_embedding_deployment,
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
    chat_deployment: Optional[str] = None,
    embedding_deployment: Optional[str] = None,
    temperature: Optional[float] = None,
    mock_mode: Optional[str] = None,
    reset: bool = False,
) -> dict:
    """更新运行时模型配置。reset=True 则清除覆盖、回退到 .env 默认。"""
    if reset:
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM app_settings WHERE key IN (?,?,?,?)",
                (KEY_CHAT, KEY_EMBED, KEY_TEMPERATURE, KEY_MOCK_MODE),
            )
        _notify_change()
        return get_model_config()

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
