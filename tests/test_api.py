"""API 集成测试（FastAPI TestClient，Mock 模式）。"""
from tests.conftest import auth


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    return r


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True
    assert body["backend"] == "chromadb"


def test_login_success_and_failure(client):
    assert login(client, "admin", "admin123").status_code == 200
    assert login(client, "admin", "wrong").status_code == 401


def test_protected_requires_token(client):
    assert client.post("/api/ingest").status_code == 401
    assert client.get("/api/stats").status_code == 401


def test_full_flow_ingest_search_ask_generate(client, admin_token):
    h = auth(admin_token)
    # 入库（demo 租户已有示例文档目录；若空则返回 0，但 seed_data 通常已生成）
    r = client.post("/api/ingest", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["backend"] == "chromadb"

    # 统计
    s = client.get("/api/stats", headers=h).json()
    assert "total_chunks" in s

    # 检索
    r = client.post("/api/search", json={"query": "数据", "top_k": 3}, headers=h)
    assert r.status_code == 200
    assert "hits" in r.json()

    # 问答
    r = client.post("/api/ask", json={"question": "有哪些能力？"}, headers=h)
    assert r.status_code == 200
    assert "answer" in r.json()

    # 生成
    r = client.post(
        "/api/generate",
        json={"customer": "测试客户", "industry": "金融", "requirements": "国产化"},
        headers=h,
    )
    assert r.status_code == 200
    g = r.json()
    assert "测试客户" in g["title"]


def test_export_endpoints(client, admin_token):
    h = auth(admin_token)
    body = {"title": "导出测试标书", "content": "# 标题\n\n## 章节\n正文**加粗**。"}
    rd = client.post("/api/export/docx", json=body, headers=h)
    assert rd.status_code == 200
    assert rd.content[:2] == b"PK"
    rp = client.post("/api/export/pdf", json=body, headers=h)
    assert rp.status_code == 200
    assert rp.content[:5] == b"%PDF-"


def test_template_crud_via_api(client, admin_token):
    h = auth(admin_token)
    # 列表含内置
    r = client.get("/api/templates", headers=h)
    assert r.status_code == 200
    assert any(t["builtin"] for t in r.json())
    # 创建
    r = client.post("/api/templates", json={"name": "API模板", "sections": ["A", "B"]}, headers=h)
    assert r.status_code == 200
    tid = r.json()["id"]
    # 用于生成
    r = client.post(
        "/api/generate",
        json={"customer": "C", "industry": "x", "requirements": "y", "template_id": tid},
        headers=h,
    )
    assert r.status_code == 200
    assert "A" in r.json()["content"] and "B" in r.json()["content"]
    # 删除
    r = client.delete(f"/api/templates/{tid}", headers=h)
    assert r.status_code == 200


def test_admin_rbac_and_audit(client, admin_token):
    h = auth(admin_token)
    # 管理员可访问
    assert client.get("/api/admin/tenants", headers=h).status_code == 200
    # 普通用户被拒
    pres = login(client, "presales", "demo123").json()["token"]
    assert client.get("/api/admin/tenants", headers=auth(pres)).status_code == 403
    # 审计日志含 login 动作
    al = client.get("/api/admin/audit?scope=tenant", headers=h).json()
    assert any(e["action"] == "login" for e in al)


def test_tenant_isolation_via_api(client):
    # acme 登录后只应看到 acme 的数据
    acme = login(client, "acme", "acme123").json()["token"]
    h = auth(acme)
    client.post("/api/ingest", headers=h)
    r = client.post("/api/search", json={"query": "客服 零售", "top_k": 5}, headers=h)
    titles = [x["title"] for x in r.json()["hits"]]
    # 不应出现 demo 租户的政务/银行类文档
    assert not any("银行" in t or "政务" in t for t in titles)


def test_model_config_get_and_update(client, admin_token):
    h = auth(admin_token)
    # 读取
    r = client.get("/api/admin/model-config", headers=h)
    assert r.status_code == 200
    cfg = r.json()
    assert "chat_deployment" in cfg and "chat_presets" in cfg

    # 更新 chat 模型
    r = client.put("/api/admin/model-config",
                   json={"chat_deployment": "gpt-4o-mini", "temperature": 0.7}, headers=h)
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["chat_deployment"] == "gpt-4o-mini"
    assert cfg["chat_overridden"] is True
    assert cfg["temperature"] == 0.7

    # 审计记录包含 update_model_config
    al = client.get("/api/admin/audit?scope=tenant", headers=h).json()
    assert any(e["action"] == "update_model_config" for e in al)

    # 恢复默认
    r = client.put("/api/admin/model-config", json={"reset": True}, headers=h)
    assert r.json()["chat_overridden"] is False


def test_model_config_requires_admin(client):
    pres = login(client, "presales", "demo123").json()["token"]
    assert client.get("/api/admin/model-config", headers=auth(pres)).status_code == 403
    assert client.put("/api/admin/model-config", json={"reset": True},
                      headers=auth(pres)).status_code == 403

