"""ChromaDB 向量库封装（按租户隔离 collection）。"""
import os
from typing import Optional

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

import logging

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.azure_client import get_llm

_client = None
_collections: dict = {}


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
    return _client


def _coll_name(tenant_id: str) -> str:
    return f"{settings.collection_name}_{tenant_id}"


def get_collection(tenant_id: str):
    if tenant_id not in _collections:
        _collections[tenant_id] = _get_client().get_or_create_collection(
            name=_coll_name(tenant_id),
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[tenant_id]


def reset_collection(tenant_id: str):
    get_collection(tenant_id)
    try:
        _get_client().delete_collection(_coll_name(tenant_id))
    except Exception:
        pass
    _collections.pop(tenant_id, None)
    return get_collection(tenant_id)


def add_documents(tenant_id: str, ids, texts, metadatas):
    col = get_collection(tenant_id)
    embeddings = get_llm().embed(texts)
    col.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)


def query(
    tenant_id: str,
    text: str,
    top_k: int,
    doc_type: Optional[str] = None,
    department: Optional[str] = None,
) -> list[dict]:
    col = get_collection(tenant_id)
    if col.count() == 0:
        return []
    embedding = get_llm().embed([text])[0]

    where_clauses = []
    if doc_type:
        where_clauses.append({"doc_type": doc_type})
    if department:
        where_clauses.append({"department": department})
    where: Optional[dict] = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    res = col.query(
        query_embeddings=[embedding],
        n_results=min(top_k, col.count()),
        where=where,
    )
    hits = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        hits.append(
            {
                "text": doc,
                "score": round(1.0 - float(dist), 4),
                "title": meta.get("title", ""),
                "doc_type": meta.get("doc_type", ""),
                "department": meta.get("department", ""),
                "industry": meta.get("industry", ""),
                "source": meta.get("source", ""),
            }
        )
    return hits


def stats(tenant_id: str) -> dict:
    col = get_collection(tenant_id)
    total = col.count()
    by_doc_type: dict = {}
    by_department: dict = {}
    if total:
        data = col.get(include=["metadatas"])
        for meta in data.get("metadatas", []):
            meta = meta or {}
            dt = meta.get("doc_type", "未知")
            dp = meta.get("department", "未知")
            by_doc_type[dt] = by_doc_type.get(dt, 0) + 1
            by_department[dp] = by_department.get(dp, 0) + 1
    return {"total": total, "by_doc_type": by_doc_type, "by_department": by_department}
