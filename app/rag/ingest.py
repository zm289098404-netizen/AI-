"""文档解析、中文友好分块、入库（按租户）。"""
import json
import re
from pathlib import Path

from app.config import settings
from app.rag.retriever import get_backend


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _read_docx(path: Path) -> str:
    import docx

    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs)


def read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return _read_txt(path)
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    return ""


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """按段落聚合，超长则按字数滑窗切分（中文按字符）。"""
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 1 <= size:
            buf = f"{buf}\n{para}" if buf else para
        else:
            if buf:
                chunks.append(buf)
            if len(para) <= size:
                buf = para
            else:
                start = 0
                while start < len(para):
                    chunks.append(para[start : start + size])
                    start += size - overlap
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


def _parse_meta(path: Path, raw: str) -> tuple[dict, str]:
    """支持文件头部 JSON front-matter (--- 包裹) 提供元数据。"""
    meta = {
        "title": path.stem,
        "doc_type": "其他",
        "department": "未知",
        "industry": "通用",
        "source": path.name,
    }
    body = raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if m:
        try:
            front = json.loads(m.group(1))
            for k in ("title", "doc_type", "department", "industry"):
                if k in front:
                    meta[k] = front[k]
            body = m.group(2)
        except json.JSONDecodeError:
            pass
    return meta, body


def ingest_directory(tenant_id: str, reset: bool = True) -> dict:
    backend = get_backend()
    if reset:
        backend.reset(tenant_id)

    data_dir = settings.tenant_data_path(tenant_id)
    files = [
        p
        for p in data_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".txt", ".md", ".pdf", ".docx")
    ]

    total_chunks = 0
    details = []
    for path in files:
        raw = read_file(path)
        if not raw.strip():
            continue
        meta, body = _parse_meta(path, raw)
        chunks = chunk_text(body, settings.chunk_size, settings.chunk_overlap)
        ids = [f"{path.stem}-{i}" for i in range(len(chunks))]
        metadatas = [dict(meta, chunk_index=i) for i in range(len(chunks))]
        if chunks:
            backend.index(tenant_id, ids, chunks, metadatas)
        total_chunks += len(chunks)
        details.append(
            {
                "file": path.name,
                "title": meta["title"],
                "doc_type": meta["doc_type"],
                "chunks": len(chunks),
            }
        )

    return {
        "files_processed": len(details),
        "chunks_indexed": total_chunks,
        "details": details,
        "backend": backend.name,
    }
