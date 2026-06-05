"""Azure 客户端 Mock 行为单元测试。"""
from app.config import settings
from app.rag.azure_client import AzureLLM, _mock_embedding


def test_mock_mode_active_without_credentials():
    assert settings.use_mock is True


def test_mock_embedding_dimension_and_determinism():
    v1 = _mock_embedding("国产化数据库")
    v2 = _mock_embedding("国产化数据库")
    assert len(v1) == 256
    assert v1 == v2  # 确定性


def test_mock_embedding_normalized():
    v = _mock_embedding("测试文本")
    norm = sum(x * x for x in v) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_mock_embedding_differs_for_different_text():
    assert _mock_embedding("金融") != _mock_embedding("制造")


def test_llm_embed_batch():
    llm = AzureLLM()
    out = llm.embed(["甲", "乙", "丙"])
    assert len(out) == 3
    assert all(len(e) == 256 for e in out)


def test_llm_chat_mock_contains_context():
    llm = AzureLLM()
    ans = llm.chat("system", "user question", context="这是检索到的上下文片段")
    assert "Mock" in ans
    assert "这是检索到的上下文片段" in ans
