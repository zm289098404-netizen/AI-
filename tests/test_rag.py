"""检索、问答、标书生成与多租户隔离单元测试（Mock 模式）。"""
from app.rag import generator, ingest
from app.rag.retriever import get_backend


def test_backend_is_chromadb_in_mock():
    assert get_backend().name == "chromadb"


def test_search_returns_relevant_hits(seeded_tenant):
    hits = generator.search(seeded_tenant, "国产数据库", top_k=2)
    assert len(hits) >= 1
    assert any("数据" in h["title"] or "案例" in h["doc_type"] for h in hits)
    # 每个命中包含完整元数据
    for h in hits:
        assert set(["text", "score", "title", "doc_type", "department", "industry"]).issubset(h)


def test_search_filter_by_doc_type(seeded_tenant):
    hits = generator.search(seeded_tenant, "国产化", top_k=5, doc_type="案例")
    assert hits  # 应有结果
    assert all(h["doc_type"] == "案例" for h in hits)


def test_stats_counts(seeded_tenant):
    s = get_backend().stats(seeded_tenant)
    assert s["total"] >= 2
    assert "案例" in s["by_doc_type"]
    assert "产品" in s["by_doc_type"]


def test_ask_returns_citations(seeded_tenant):
    r = generator.ask(seeded_tenant, "我们有哪些国产化能力？")
    assert r["mock_mode"] is True
    assert isinstance(r["citations"], list)
    assert len(r["citations"]) >= 1
    assert r["answer"]


def test_generate_bid_uses_sections(seeded_tenant):
    sections = ["背景", "方案", "案例"]
    r = generator.generate_bid(
        seeded_tenant, customer="某客户", industry="金融",
        requirements="国产化替代", sections=sections,
    )
    assert "某客户" in r["title"]
    # Mock 生成应包含所有指定章节
    assert all(sec in r["content"] for sec in sections)
    assert r["citations"]


def test_tenant_isolation_empty_for_new_tenant():
    # 未入库的新租户检索应为空
    hits = generator.search("brand_new_tenant", "任意查询", top_k=3)
    assert hits == []


def test_ingest_directory_idempotent_reset(seeded_tenant):
    # 再次 ingest（reset）后片段数应保持稳定，不累积
    before = get_backend().stats(seeded_tenant)["total"]
    ingest.ingest_directory(seeded_tenant, reset=True)
    after = get_backend().stats(seeded_tenant)["total"]
    assert after == before
