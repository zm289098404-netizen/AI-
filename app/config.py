from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Azure OpenAI ----
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # ---- Azure AI Search (hybrid retrieval) ----
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_prefix: str = "bidkb"
    embedding_dim: int = 256  # mock/真实向量维度需一致

    # ---- 数据与向量库路径 ----
    data_dir: str = "data/knowledge"
    chroma_dir: str = "data/chroma"
    app_db_dir: str = "data"
    collection_name: str = "bid_knowledge"

    # ---- 分块/检索 ----
    chunk_size: int = 280
    chunk_overlap: int = 80
    top_k: int = 5

    # ---- 认证 ----
    auth_secret: str = "dev-secret-change-me"
    token_ttl_hours: int = 12

    @property
    def knowledge_root(self) -> Path:
        p = BASE_DIR / self.data_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    def tenant_data_path(self, tenant_id: str) -> Path:
        p = self.knowledge_root / tenant_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> Path:
        p = BASE_DIR / self.chroma_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def app_db_path(self) -> Path:
        p = BASE_DIR / self.app_db_dir
        p.mkdir(parents=True, exist_ok=True)
        return p / "app.db"

    @property
    def use_mock(self) -> bool:
        """无 Azure OpenAI 凭据时自动降级为 Mock 模式。"""
        return not (self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def use_azure_search(self) -> bool:
        """配置了 Azure AI Search 时启用混合检索后端。"""
        return bool(self.azure_search_endpoint and self.azure_search_api_key)


settings = Settings()
