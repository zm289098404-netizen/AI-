import io
import re
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app import auth, export, audit, templates_store, settings_store
from app.models import (
    LoginRequest, LoginResponse, MeResponse, TenantInfo,
    CreateTenantRequest, CreateUserRequest,
    IngestResponse, SearchRequest, SearchResponse,
    AskRequest, AskResponse, GenerateRequest, GenerateResponse,
    StatsResponse, ExportRequest,
    TemplateInfo, CreateTemplateRequest, AuditEntry,
    ModelConfig, UpdateModelConfigRequest,
)
from app.rag import ingest, generator
from app.rag.retriever import get_backend

app = FastAPI(title="智能投标/方案生成系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.on_event("startup")
def _startup():
    auth.ensure_seed_accounts()


# ---------------- 认证 ----------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    user = auth.verify_user(req.username, req.password)
    if not user:
        raise HTTPException(401, "用户名或密码错误")
    token = auth.make_token(user)
    audit.log(user["username"], user["tenant_id"], "login", {"role": user["role"]})
    return LoginResponse(
        token=token, username=user["username"], display_name=user["display_name"],
        tenant_id=user["tenant_id"], role=user["role"],
    )


@app.get("/api/auth/me", response_model=MeResponse)
def me(user: dict = Depends(auth.get_current_user)):
    return MeResponse(
        username=user["sub"], display_name=user.get("display_name", user["sub"]),
        tenant_id=user["tenant_id"], role=user["role"],
    )


# ---------------- 管理（多租户） ----------------
@app.get("/api/admin/tenants", response_model=list[TenantInfo])
def list_tenants(_: dict = Depends(auth.require_admin)):
    return [TenantInfo(**t) for t in auth.list_tenants()]


@app.post("/api/admin/tenants", response_model=TenantInfo)
def create_tenant(req: CreateTenantRequest, admin: dict = Depends(auth.require_admin)):
    if not re.match(r"^[a-zA-Z0-9_-]+$", req.id):
        raise HTTPException(400, "租户标识仅允许英文/数字/_-")
    audit.log(admin["sub"], admin["tenant_id"], "create_tenant", {"id": req.id, "name": req.name})
    return TenantInfo(**auth.create_tenant(req.id, req.name))


@app.post("/api/admin/users")
def create_user(req: CreateUserRequest, admin: dict = Depends(auth.require_admin)):
    audit.log(admin["sub"], admin["tenant_id"], "create_user",
              {"username": req.username, "tenant_id": req.tenant_id, "role": req.role})
    return auth.create_user(
        req.username, req.password, req.tenant_id, role=req.role,
        display_name=req.display_name,
    )


@app.get("/api/admin/audit", response_model=list[AuditEntry])
def get_audit(scope: str = "tenant", admin: dict = Depends(auth.require_admin)):
    tenant = None if scope == "all" else admin["tenant_id"]
    return [AuditEntry(**e) for e in audit.recent(tenant_id=tenant, limit=200)]


# ---------------- AI 模型配置（管理端） ----------------
@app.get("/api/admin/model-config", response_model=ModelConfig)
def get_model_config(_: dict = Depends(auth.require_admin)):
    return ModelConfig(**settings_store.get_model_config())


@app.put("/api/admin/model-config", response_model=ModelConfig)
def update_model_config(req: UpdateModelConfigRequest, admin: dict = Depends(auth.require_admin)):
    cfg = settings_store.update_model_config(
        provider=req.provider,
        base_url=req.base_url,
        api_key=req.api_key,
        azure_endpoint=req.azure_endpoint,
        api_version=req.api_version,
        chat_deployment=req.chat_deployment,
        embedding_deployment=req.embedding_deployment,
        temperature=req.temperature,
        mock_mode=req.mock_mode,
        clear_api_key=req.clear_api_key,
        reset=req.reset,
    )
    audit.log(admin["sub"], admin["tenant_id"], "update_model_config",
              {"provider": cfg["provider"], "chat": cfg["chat_deployment"], "embedding": cfg["embedding_deployment"],
               "temperature": cfg["temperature"], "mock_mode_setting": cfg["mock_mode_setting"],
               "api_key_set": cfg["api_key_set"],
               "reset": req.reset})
    return ModelConfig(**cfg)


# ---------------- 章节模板 ----------------
@app.get("/api/templates", response_model=list[TemplateInfo])
def list_templates(user: dict = Depends(auth.get_current_user)):
    return [TemplateInfo(**t) for t in templates_store.list_templates(user["tenant_id"])]


@app.post("/api/templates", response_model=TemplateInfo)
def create_template(req: CreateTemplateRequest, user: dict = Depends(auth.get_current_user)):
    t = templates_store.create_template(user["tenant_id"], req.name, req.sections)
    audit.log(user["sub"], user["tenant_id"], "create_template", {"name": req.name})
    return TemplateInfo(**t)


@app.delete("/api/templates/{template_id:path}")
def delete_template(template_id: str, user: dict = Depends(auth.get_current_user)):
    templates_store.delete_template(user["tenant_id"], template_id)
    audit.log(user["sub"], user["tenant_id"], "delete_template", {"id": template_id})
    return {"deleted": template_id}


# ---------------- 知识库 ----------------
@app.post("/api/ingest", response_model=IngestResponse)
def api_ingest(user: dict = Depends(auth.get_current_user)):
    result = ingest.ingest_directory(user["tenant_id"], reset=True)
    audit.log(user["sub"], user["tenant_id"], "ingest",
              {"files": result["files_processed"], "chunks": result["chunks_indexed"]})
    return IngestResponse(mock_mode=settings_store.effective_mock(), **result)


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...), user: dict = Depends(auth.get_current_user)
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".txt", ".md", ".pdf", ".docx"):
        raise HTTPException(400, "仅支持 txt/md/pdf/docx 文件")
    dest = settings.tenant_data_path(user["tenant_id"]) / file.filename
    dest.write_bytes(await file.read())
    return {"saved": file.filename, "hint": "上传后请点击『重建知识库索引』使其生效"}


@app.post("/api/search", response_model=SearchResponse)
def api_search(req: SearchRequest, user: dict = Depends(auth.get_current_user)):
    hits = generator.search(
        user["tenant_id"], req.query, top_k=req.top_k,
        doc_type=req.doc_type, department=req.department,
    )
    return SearchResponse(hits=hits)


@app.post("/api/ask", response_model=AskResponse)
def api_ask(req: AskRequest, user: dict = Depends(auth.get_current_user)):
    result = generator.ask(
        user["tenant_id"], req.question, top_k=req.top_k,
        doc_type=req.doc_type, department=req.department,
    )
    return AskResponse(**result)


@app.post("/api/generate", response_model=GenerateResponse)
def api_generate(req: GenerateRequest, user: dict = Depends(auth.get_current_user)):
    sections = req.sections or templates_store.resolve_sections(
        user["tenant_id"], req.template_id
    )
    result = generator.generate_bid(
        user["tenant_id"], customer=req.customer, industry=req.industry,
        requirements=req.requirements, sections=sections, top_k=req.top_k,
    )
    audit.log(user["sub"], user["tenant_id"], "generate",
              {"customer": req.customer, "industry": req.industry,
               "template_id": req.template_id})
    return GenerateResponse(**result)


@app.get("/api/stats", response_model=StatsResponse)
def api_stats(user: dict = Depends(auth.get_current_user)):
    s = get_backend().stats(user["tenant_id"])
    return StatsResponse(
        total_chunks=s["total"], by_doc_type=s["by_doc_type"],
        by_department=s["by_department"], mock_mode=settings_store.effective_mock(),
        backend=get_backend().name,
    )


# ---------------- 导出 ----------------
def _safe_name(title: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", title).strip() or "标书"
    return name


@app.post("/api/export/docx")
def export_docx(req: ExportRequest, user: dict = Depends(auth.get_current_user)):
    data = export.to_docx(req.title, req.content)
    audit.log(user["sub"], user["tenant_id"], "export_docx", {"title": req.title})
    fname = _safe_name(req.title) + ".docx"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{_url(fname)}"}
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@app.post("/api/export/pdf")
def export_pdf(req: ExportRequest, user: dict = Depends(auth.get_current_user)):
    data = export.to_pdf(req.title, req.content)
    audit.log(user["sub"], user["tenant_id"], "export_pdf", {"title": req.title})
    fname = _safe_name(req.title) + ".pdf"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{_url(fname)}"}
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=headers)


def _url(s: str) -> str:
    from urllib.parse import quote

    return quote(s)


# ---------------- 健康/前端 ----------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mock_mode": settings_store.effective_mock(),
        "backend": get_backend().name,
        "azure_search": settings.use_azure_search,
    }


@app.get("/")
def index():
    return FileResponse(str(WEB_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
