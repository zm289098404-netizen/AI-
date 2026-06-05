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
        self.mock = settings.use_mock
        self._client = None
        if not self.mock:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.mock:
            return [_mock_embedding(t) for t in texts]
        resp = self._client.embeddings.create(
            model=settings.azure_openai_embedding_deployment,
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def chat(self, system: str, user: str, context: str = "") -> str:
        if self.mock:
            return _mock_chat(system, user, context)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = self._client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=messages,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""


_llm: Optional[AzureLLM] = None


def get_llm() -> AzureLLM:
    global _llm
    if _llm is None:
        _llm = AzureLLM()
    return _llm
