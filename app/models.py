from typing import Optional
from pydantic import BaseModel, Field


# ---- 认证 ----
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    display_name: str
    tenant_id: str
    role: str


class MeResponse(BaseModel):
    username: str
    display_name: str
    tenant_id: str
    role: str


class TenantInfo(BaseModel):
    id: str
    name: str


class CreateTenantRequest(BaseModel):
    id: str = Field(..., description="租户标识(英文/数字)")
    name: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    tenant_id: str
    role: str = "user"
    display_name: Optional[str] = None


# ---- 知识库 / 检索 ----
class IngestResponse(BaseModel):
    files_processed: int
    chunks_indexed: int
    mock_mode: bool
    backend: str = "chromadb"
    details: list[dict] = []


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    doc_type: Optional[str] = None
    department: Optional[str] = None


class SearchHit(BaseModel):
    text: str
    score: float
    title: str
    doc_type: str
    department: str
    industry: str
    source: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = None
    doc_type: Optional[str] = None
    department: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    citations: list[SearchHit]
    mock_mode: bool


class GenerateRequest(BaseModel):
    customer: str
    industry: str = ""
    requirements: str
    sections: Optional[list[str]] = None
    template_id: Optional[str] = Field(None, description="章节模板 id；优先级低于显式 sections")
    top_k: Optional[int] = None


class GenerateResponse(BaseModel):
    title: str
    content: str
    citations: list[SearchHit]
    mock_mode: bool


class StatsResponse(BaseModel):
    total_chunks: int
    by_doc_type: dict
    by_department: dict
    mock_mode: bool
    backend: str = "chromadb"


class ExportRequest(BaseModel):
    title: str
    content: str


# ---- 模板 ----
class TemplateInfo(BaseModel):
    id: str
    name: str
    sections: list[str]
    builtin: bool
    category: str = "自定义"


class CreateTemplateRequest(BaseModel):
    name: str
    sections: list[str]
    category: Optional[str] = None


# ---- 审计 ----
class AuditEntry(BaseModel):
    ts: float
    time: str
    username: str
    tenant_id: str
    action: str
    detail: str


# ---- AI 模型配置 ----
class ModelConfig(BaseModel):
    provider: str
    provider_mode: str
    provider_presets: list[dict]
    base_url: str
    azure_endpoint: str
    api_version: str
    api_key_set: bool
    api_key_masked: str
    chat_deployment: str
    embedding_deployment: str
    temperature: float
    chat_default: str
    embedding_default: str
    provider_overridden: bool
    base_url_overridden: bool
    azure_endpoint_overridden: bool
    api_key_overridden: bool
    chat_overridden: bool
    embedding_overridden: bool
    temperature_overridden: bool
    chat_presets: list[str]
    embedding_presets: list[str]
    mock_mode_setting: str
    mock_mode: bool
    has_credentials: bool
    backend: str


class UpdateModelConfigRequest(BaseModel):
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, description="留空表示不修改现有 API Key")
    azure_endpoint: Optional[str] = None
    api_version: Optional[str] = None
    chat_deployment: Optional[str] = None
    embedding_deployment: Optional[str] = None
    temperature: Optional[float] = None
    mock_mode: Optional[str] = Field(None, description="auto | on | off")
    clear_api_key: bool = False
    reset: bool = False


class TestConnectionResponse(BaseModel):
    ok: bool
    mode: str
    message: str
    latency_ms: int = 0
    sample: str = ""


class SystemSettings(BaseModel):
    deployment_mode: str
    brand_name: str
    default_brand_name: str
    deployment_modes: list[str]


class UpdateSystemSettingsRequest(BaseModel):
    deployment_mode: Optional[str] = Field(None, description="demo | production")
    brand_name: Optional[str] = None


class PublicSystemInfo(BaseModel):
    """登录前可读取的公开信息（不含密钥）。"""
    brand_name: str
    deployment_mode: str
    backend: str
    mock_mode: bool
