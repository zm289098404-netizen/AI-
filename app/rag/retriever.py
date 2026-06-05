"""检索后端抽象：本地 ChromaDB 或 Azure AI Search（混合检索）。

- 未配置 Azure AI Search 时使用 ChromaDB（本地、零运维）。
- 配置后自动切换为 Azure AI Search，执行 向量 + 关键词 的混合检索。
两种后端均按租户隔离（collection / index 维度）。
"""
from typing import Optional

from app.config import settings
from app.rag import store
from app.rag.azure_client import get_llm


class BaseBackend:
    name = "base"

    def reset(self, tenant_id: str):
        raise NotImplementedError

    def index(self, tenant_id, ids, texts, metadatas):
        raise NotImplementedError

    def query(self, tenant_id, text, top_k, doc_type=None, department=None) -> list[dict]:
        raise NotImplementedError

    def stats(self, tenant_id) -> dict:
        raise NotImplementedError


class ChromaBackend(BaseBackend):
    name = "chromadb"

    def reset(self, tenant_id):
        store.reset_collection(tenant_id)

    def index(self, tenant_id, ids, texts, metadatas):
        store.add_documents(tenant_id, ids, texts, metadatas)

    def query(self, tenant_id, text, top_k, doc_type=None, department=None):
        return store.query(tenant_id, text, top_k, doc_type=doc_type, department=department)

    def stats(self, tenant_id):
        return store.stats(tenant_id)


class AzureSearchBackend(BaseBackend):
    """Azure AI Search 混合检索（vector + keyword）。"""

    name = "azure_search"

    def __init__(self):
        from azure.core.credentials import AzureKeyCredential

        self._cred = AzureKeyCredential(settings.azure_search_api_key)
        self._endpoint = settings.azure_search_endpoint
        self._ensured: set = set()

    def _index_name(self, tenant_id: str) -> str:
        return f"{settings.azure_search_index_prefix}-{tenant_id}".lower()

    def _search_client(self, tenant_id: str):
        from azure.search.documents import SearchClient

        return SearchClient(self._endpoint, self._index_name(tenant_id), self._cred)

    def _index_client(self):
        from azure.search.documents.indexes import SearchIndexClient

        return SearchIndexClient(self._endpoint, self._cred)

    def _ensure_index(self, tenant_id: str):
        if tenant_id in self._ensured:
            return
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SimpleField,
            SearchableField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
        )

        name = self._index_name(tenant_id)
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SimpleField(name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="department", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="industry", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="source", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=settings.embedding_dim,
                vector_search_profile_name="vprofile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[VectorSearchProfile(name="vprofile", algorithm_configuration_name="hnsw")],
        )
        index = SearchIndex(name=name, fields=fields, vector_search=vector_search)
        ic = self._index_client()
        ic.create_or_update_index(index)
        self._ensured.add(tenant_id)

    def reset(self, tenant_id):
        ic = self._index_client()
        try:
            ic.delete_index(self._index_name(tenant_id))
        except Exception:
            pass
        self._ensured.discard(tenant_id)
        self._ensure_index(tenant_id)

    def index(self, tenant_id, ids, texts, metadatas):
        self._ensure_index(tenant_id)
        vectors = get_llm().embed(texts)
        docs = []
        for _id, text, meta, vec in zip(ids, texts, metadatas, vectors):
            docs.append(
                {
                    "id": str(_id),
                    "content": text,
                    "title": meta.get("title", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "department": meta.get("department", ""),
                    "industry": meta.get("industry", ""),
                    "source": meta.get("source", ""),
                    "content_vector": vec,
                }
            )
        self._search_client(tenant_id).upload_documents(documents=docs)

    def query(self, tenant_id, text, top_k, doc_type=None, department=None):
        from azure.search.documents.models import VectorizedQuery

        self._ensure_index(tenant_id)
        vector = get_llm().embed([text])[0]
        vq = VectorizedQuery(
            vector=vector, k_nearest_neighbors=top_k, fields="content_vector"
        )
        filters = []
        if doc_type:
            filters.append(f"doc_type eq '{doc_type}'")
        if department:
            filters.append(f"department eq '{department}'")
        flt = " and ".join(filters) if filters else None
        try:
            results = self._search_client(tenant_id).search(
                search_text=text,
                vector_queries=[vq],
                filter=flt,
                top=top_k,
            )
        except Exception:
            return []
        hits = []
        for r in results:
            hits.append(
                {
                    "text": r.get("content", ""),
                    "score": round(float(r.get("@search.score", 0.0)), 4),
                    "title": r.get("title", ""),
                    "doc_type": r.get("doc_type", ""),
                    "department": r.get("department", ""),
                    "industry": r.get("industry", ""),
                    "source": r.get("source", ""),
                }
            )
        return hits

    def stats(self, tenant_id):
        try:
            sc = self._search_client(tenant_id)
            total = sc.get_document_count()
            res = sc.search(search_text="*", facets=["doc_type,count:50", "department,count:50"], top=0)
            facets = res.get_facets() or {}
            by_doc_type = {f["value"]: f["count"] for f in facets.get("doc_type", [])}
            by_department = {f["value"]: f["count"] for f in facets.get("department", [])}
            return {"total": total, "by_doc_type": by_doc_type, "by_department": by_department}
        except Exception:
            return {"total": 0, "by_doc_type": {}, "by_department": {}}


_backend: Optional[BaseBackend] = None


def get_backend() -> BaseBackend:
    global _backend
    if _backend is None:
        if settings.use_azure_search:
            _backend = AzureSearchBackend()
        else:
            _backend = ChromaBackend()
    return _backend


def backend_name() -> str:
    return get_backend().name
