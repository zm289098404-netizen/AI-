"""Azure OpenAI 封装，含 Mock 降级，保证无凭据时也能跑通完整流程。"""
import hashlib
import math
from typing import Optional

from app.config import settings


_EMBED_DIM = 256


def _mock_embedding(text: str) -> list[float]:
    """基于字符 hash 的确定性伪向量，保证同文本同向量、近义可部分重合。"""
    vec = [0.0] * _EMBED_DIM
    tokens = text.lower().split() or [text]
    for tok in tokens:
        for ch in tok:
            h = int(hashlib.md5(ch.encode("utf-8")).hexdigest(), 16)
            vec[h % _EMBED_DIM] += 1.0
    # 也按字符级累加（中文无空格）
    for ch in text:
        h = int(hashlib.md5(ch.encode("utf-8")).hexdigest(), 16)
        vec[h % _EMBED_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _mock_chat(system: str, user: str, context: str) -> str:
    snippet = context.strip()
    if len(snippet) > 1200:
        snippet = snippet[:1200] + "…"
    return (
        "【Mock 模式输出 — 未配置 Azure OpenAI 凭据】\n\n"
        "以下内容基于检索到的知识库片段自动汇总（占位生成，配置真实凭据后将由大模型生成）：\n\n"
        f"{snippet}\n\n"
        "—— 以上为检索增强占位回答，请在 .env 中配置 AZURE_OPENAI_ENDPOINT 与 "
        "AZURE_OPENAI_API_KEY 以启用真实生成。"
    )


class AzureLLM:
    def __init__(self) -> None:
        self._client = None

    @property
    def mock(self) -> bool:
        from app import settings_store

        return settings_store.effective_mock()

    def _get_client(self):
        """惰性创建 AzureOpenAI 客户端（仅真实模式需要）。"""
        if self._client is None:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.mock:
            return [_mock_embedding(t) for t in texts]
        from app import settings_store

        resp = self._get_client().embeddings.create(
            model=settings_store.embedding_deployment(),
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def chat(self, system: str, user: str, context: str = "") -> str:
        if self.mock:
            return _mock_chat(system, user, context)
        from app import settings_store

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = self._get_client().chat.completions.create(
            model=settings_store.chat_deployment(),
            messages=messages,
            temperature=settings_store.temperature(),
        )
        return resp.choices[0].message.content or ""


_llm: Optional[AzureLLM] = None


def get_llm() -> AzureLLM:
    global _llm
    if _llm is None:
        _llm = AzureLLM()
    return _llm


def reset_llm() -> None:
    """清除缓存的 LLM 客户端，使配置变更（含 Mock 切换）即时生效。"""
    global _llm
    _llm = None
