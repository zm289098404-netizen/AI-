"""pytest 全局夹具：将所有持久化路径重定向到临时目录，保证测试隔离。

注意：必须在导入任何 app.* 模块之前设置环境变量，因为 app.config.settings
在导入时即被实例化。
"""
import os
import tempfile
from pathlib import Path

import pytest

# ---- 在导入 app 之前重定向路径到临时目录 ----
_TMP = Path(tempfile.mkdtemp(prefix="bidtest_"))
os.environ["DATA_DIR"] = str(_TMP / "knowledge")
os.environ["CHROMA_DIR"] = str(_TMP / "chroma")
os.environ["APP_DB_DIR"] = str(_TMP / "db")
os.environ["COLLECTION_NAME"] = "test_kb"
# 确保 Mock 模式（无 Azure 凭据）
os.environ["AZURE_OPENAI_ENDPOINT"] = ""
os.environ["AZURE_OPENAI_API_KEY"] = ""
os.environ["AZURE_SEARCH_ENDPOINT"] = ""
os.environ["AZURE_SEARCH_API_KEY"] = ""
os.environ["AUTH_SECRET"] = "test-secret"


@pytest.fixture(scope="session")
def tmp_root() -> Path:
    return _TMP


def _write(d: Path, name: str, meta_json: str, body: str):
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(f"---\n{meta_json}\n---\n{body}", encoding="utf-8")


@pytest.fixture(autouse=True, scope="session")
def _seed_app_data():
    """在临时知识库目录写入 demo/acme 两个租户的示例文档（供 API 测试 ingest）。"""
    from app.config import settings

    demo = settings.tenant_data_path("demo")
    _write(demo, "case_bank.md",
           '{"title":"某银行国产化案例","doc_type":"案例","department":"市场部","industry":"金融"}',
           "某银行核心系统国产化迁移，采用国产分布式数据库，TCO 下降 35%。")
    _write(demo, "case_gov.md",
           '{"title":"某市政务一网通办","doc_type":"案例","department":"市场部","industry":"政务"}',
           "建设全市统一数据共享平台，群众办事材料减少 60%。")
    _write(demo, "product_mid.md",
           '{"title":"数据中台白皮书","doc_type":"产品","department":"技术部","industry":"通用"}',
           "数据中台支持 MySQL、达梦、人大金仓等国产数据库，实时延迟低于 3 秒。")

    acme = settings.tenant_data_path("acme")
    _write(acme, "acme_ai.md",
           '{"title":"ACME 智能客服","doc_type":"产品","department":"技术部","industry":"互联网"}',
           "基于大模型的智能客服，支持多轮对话与知识库问答。")
    _write(acme, "acme_retail.md",
           '{"title":"ACME 零售数字化案例","doc_type":"案例","department":"市场部","industry":"零售"}',
           "部署全渠道中台，会员复购率提升 25%。")
    yield


@pytest.fixture(scope="session")
def seeded_tenant():
    """为某个测试租户写入两份示例文档并入库，返回租户 id。"""
    from app.config import settings
    from app.rag import ingest

    tenant = "t_demo"
    d = settings.tenant_data_path(tenant)
    (d / "case.md").write_text(
        '---\n{"title":"银行国产化案例","doc_type":"案例","department":"市场部","industry":"金融"}\n---\n'
        "某银行核心系统国产化迁移，采用国产分布式数据库，TCO 下降 35%。",
        encoding="utf-8",
    )
    (d / "product.md").write_text(
        '---\n{"title":"数据中台白皮书","doc_type":"产品","department":"技术部","industry":"通用"}\n---\n'
        "数据中台支持 MySQL、达梦、人大金仓等国产数据库，实时延迟低于 3 秒。",
        encoding="utf-8",
    )
    ingest.ingest_directory(tenant, reset=True)
    return tenant


@pytest.fixture()
def client():
    """FastAPI TestClient，已触发 startup（建表 + 种子账号）。"""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return r.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": "Bearer " + token}
