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


# ---------------- 管理端读写 ----------------
def get_model_config() -> dict:
    """返回当前生效配置 + 默认值 + 是否被覆盖 + 运行模式。"""
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
        "mock_mode": settings.use_mock,
        "backend": "azure_search" if settings.use_azure_search else "chromadb",
    }


def update_model_config(
    chat_deployment: Optional[str] = None,
    embedding_deployment: Optional[str] = None,
    temperature: Optional[float] = None,
    reset: bool = False,
) -> dict:
    """更新运行时模型配置。reset=True 则清除覆盖、回退到 .env 默认。"""
    if reset:
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM app_settings WHERE key IN (?,?,?)",
                (KEY_CHAT, KEY_EMBED, KEY_TEMPERATURE),
            )
        return get_model_config()

    if chat_deployment is not None and chat_deployment.strip():
        _set_raw(KEY_CHAT, chat_deployment.strip())
    if embedding_deployment is not None and embedding_deployment.strip():
        _set_raw(KEY_EMBED, embedding_deployment.strip())
    if temperature is not None:
        t = max(0.0, min(2.0, float(temperature)))
        _set_raw(KEY_TEMPERATURE, str(t))
    return get_model_config()
