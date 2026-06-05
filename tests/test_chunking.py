"""文档分块与元数据解析单元测试。"""
from pathlib import Path

from app.rag.ingest import chunk_text, _parse_meta


def test_chunk_text_respects_size():
    text = "段落一。" * 50 + "\n\n" + "段落二。" * 50
    chunks = chunk_text(text, size=120, overlap=20)
    assert len(chunks) >= 2
    assert all(len(c) <= 120 for c in chunks)
    assert all(c.strip() for c in chunks)


def test_chunk_text_short_single_chunk():
    chunks = chunk_text("很短的一段话。", size=280, overlap=80)
    assert chunks == ["很短的一段话。"]


def test_chunk_text_empty():
    assert chunk_text("   \n\n  ", size=100, overlap=10) == []


def test_parse_meta_with_frontmatter(tmp_path: Path):
    raw = (
        '---\n{"title":"测试标书","doc_type":"标书","department":"售前部","industry":"政务"}\n---\n'
        "正文内容在这里。"
    )
    p = tmp_path / "doc.md"
    meta, body = _parse_meta(p, raw)
    assert meta["title"] == "测试标书"
    assert meta["doc_type"] == "标书"
    assert meta["department"] == "售前部"
    assert meta["industry"] == "政务"
    assert body.strip() == "正文内容在这里。"


def test_parse_meta_without_frontmatter(tmp_path: Path):
    p = tmp_path / "plain.md"
    meta, body = _parse_meta(p, "没有头部的纯文本。")
    assert meta["title"] == "plain"
    assert meta["doc_type"] == "其他"
    assert body == "没有头部的纯文本。"


def test_parse_meta_invalid_json_falls_back(tmp_path: Path):
    p = tmp_path / "bad.md"
    raw = "---\n{not valid json}\n---\n正文"
    meta, body = _parse_meta(p, raw)
    # 解析失败时应回退为默认元数据，且 body 保留原始内容
    assert meta["title"] == "bad"
    assert meta["doc_type"] == "其他"
