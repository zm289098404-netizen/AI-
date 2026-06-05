<p align="center">
  <img src="docs/assets/cover.svg" alt="智能投标 / 方案生成系统 — RAG 售前助手" width="100%" />
</p>

# 智能投标 / 方案生成系统（RAG 售前助手）

> 基于 RAG 的售前知识助手 · FastAPI + Azure OpenAI + ChromaDB · 开箱即用（含 Mock 模式）

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![License](https://img.shields.io/badge/License-MIT-green)

**中文** | [English](README.en.md)

基于 **RAG（检索增强生成）** 的智能售前助手：汇聚公司历年标书、成功案例与产品文档，
帮助售前/市场/技术团队快速检索知识、智能问答，并一键生成结构化标书初稿，
显著缩短 RFP 响应周期、整合跨团队知识资产。

## ✨ 核心功能
- 📚 **知识库构建**：解析 PDF / Word / Markdown / TXT，中文智能分块，向量化入库。
- 🔎 **语义/混合检索**：按文档类型（标书/案例/产品）、部门过滤；可选 Azure AI Search 混合检索。
- 💬 **智能问答**：检索增强 + 带来源引用的专业回答。
- 📝 **标书生成**：输入 RFP 需求 → 检索匹配案例/产品 → 生成多章节标书初稿（含引用）。
- 📐 **自定义章节模板**：内置 3 套模板 + 租户级自定义模板（CRUD），生成时自由选择。
- 📤 **一键导出**：将生成的标书导出为 **Word(.docx)** 或 **PDF**（中文字体内嵌）。
- 🔐 **用户登录 + 多租户**：账号体系 + 按租户隔离的知识库（数据互不可见）。
- 🧾 **操作审计日志**：记录登录/入库/生成/导出/管理等关键动作，管理员可查。
- 🤖 **AI 模型热切换**：管理员可在管理端切换 Chat / Embedding 模型部署与生成温度，并自由切换 **Mock / 真实 Azure 模式**（auto/强制开/强制关），即时生效。
- 🐳 **容器化**：提供 Dockerfile + docker-compose，一键本地起服务。
- 🔌 **Azure OpenAI**：未配置凭据时自动降级 **Mock 模式**，无需凭据即可演示全流程。

## 🏗️ 技术栈
Python 3.11 · FastAPI · Azure OpenAI（Chat + Embedding）· ChromaDB / Azure AI Search ·
bcrypt + HMAC 令牌 · python-docx + reportlab · 原生 Web 前端

## 🚀 快速开始（Windows）

```powershell
cd d:\AI_Build\智能投标系统

# 1. 创建虚拟环境（Python 3.11）
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置（可选；不配置则运行 Mock 模式）
Copy-Item .env.example .env

# 4. 生成中文示例知识库（多租户：demo + acme）
python scripts\seed_data.py

# 5. 启动服务
uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000 ，使用下方演示账号登录，在『📚 知识库』点击 **重建知识库索引** 即可使用。

> 💡 **更快的方式**：直接运行 `./run.ps1`（Windows）或 `bash run.sh`（Linux/macOS），
> 脚本会自动建虚拟环境、装依赖、生成示例数据并启动服务。

### 🐳 使用 Docker
```bash
cp .env.example .env          # 可选，留空即 Mock 模式
docker compose up --build
```
访问 http://localhost:8000 。知识库文档、向量索引与用户库通过卷持久化。

## 👤 演示账号
| 用户名 | 密码 | 租户 | 角色 |
|--------|------|------|------|
| admin | admin123 | demo | 管理员 |
| presales | demo123 | demo | 普通用户 |
| acme | acme123 | acme | 管理员 |

> 多租户隔离：`demo` 与 `acme` 拥有各自独立的知识库与向量索引，互不可见。
> 管理员可在『⚙️ 管理』面板新增租户/用户、查看审计日志；所有用户可在『📐 章节模板』维护模板。

## 📂 目录结构
```
app/
  config.py          配置（Azure / 路径 / 认证）
  db.py              共享 SQLite 连接与统一建表
  auth.py            用户/租户、bcrypt 口令、HMAC 令牌
  templates_store.py 章节模板（内置 + 自定义 CRUD）
  audit.py           操作审计日志
  export.py          Markdown → Word / PDF（CJK 安全）
  models.py          Pydantic 模型
  main.py            FastAPI 路由
  rag/
    azure_client.py  Azure OpenAI 封装（含 Mock 降级）
    store.py         ChromaDB（按租户隔离 collection）
    retriever.py     检索后端抽象：ChromaDB / Azure AI Search 混合检索
    ingest.py        解析 + 分块 + 入库
    generator.py     问答 + 标书生成
web/                 前端（index.html / app.js / styles.css）
data/
  knowledge/<tenant>/  各租户知识库文档
  chroma/              向量持久化
  app.db               用户/租户/模板/审计库(SQLite)
scripts/
  seed_data.py       多租户示例数据
  smoke_test.py      端到端测试脚本
tests/               pytest 单元/集成测试（48 项）
Dockerfile / docker-compose.yml   容器化
run.ps1 / run.sh     一键启动脚本
.github/workflows/ci.yml          GitHub Actions CI（自动跑 smoke_test）
```

## 🔑 配置说明（.env）
| 变量 | 说明 |
|------|------|
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` | 留空启用 Mock |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | 对话模型部署名（如 gpt-4o） |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | 向量模型部署名（如 text-embedding-3-small） |
| `AZURE_SEARCH_ENDPOINT` / `AZURE_SEARCH_API_KEY` | 留空用 ChromaDB；配置后启用 Azure AI Search 混合检索 |
| `EMBEDDING_DIM` | 向量维度：Mock=256，真实 text-embedding-3-small=1536（需同步） |
| `AUTH_SECRET` | 令牌签名密钥（生产务必修改） |
| `TOKEN_TTL_HOURS` | 令牌有效期 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TOP_K` | 分块与检索参数 |

## 📡 API
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/auth/login` | 登录获取令牌 | 否 |
| GET  | `/api/auth/me` | 当前用户 | Bearer |
| POST | `/api/ingest` | 重建本租户索引 | Bearer |
| POST | `/api/upload` | 上传文档 | Bearer |
| POST | `/api/search` | 语义/混合检索 | Bearer |
| POST | `/api/ask` | 智能问答 | Bearer |
| POST | `/api/generate` | 生成标书初稿（支持 `template_id`） | Bearer |
| GET  | `/api/templates` | 模板列表（内置+自定义） | Bearer |
| POST | `/api/templates` | 新建自定义模板 | Bearer |
| DELETE | `/api/templates/{id}` | 删除自定义模板 | Bearer |
| POST | `/api/export/docx` | 导出 Word | Bearer |
| POST | `/api/export/pdf` | 导出 PDF | Bearer |
| GET  | `/api/stats` | 知识库统计 | Bearer |
| GET  | `/api/admin/tenants` | 租户列表 | Admin |
| POST | `/api/admin/tenants` | 新增租户 | Admin |
| POST | `/api/admin/users` | 新增用户 | Admin |
| GET  | `/api/admin/audit` | 审计日志（`scope=tenant\|all`） | Admin |
| GET  | `/api/admin/model-config` | 查看 AI 模型配置 | Admin |
| PUT  | `/api/admin/model-config` | 切换 Chat/Embedding 模型与温度 | Admin |

## 🔎 切换到 Azure AI Search 混合检索
在 `.env` 配置 `AZURE_SEARCH_ENDPOINT` 与 `AZURE_SEARCH_API_KEY`（并将 `EMBEDDING_DIM`
设为真实向量维度），重启后系统自动：为每个租户创建独立索引、上传向量、执行
**向量 + 关键词** 的混合检索；前端状态栏会显示当前后端。

## 📌 自定义文档元数据
在文档头部添加 JSON front-matter 即可携带元数据：
```
---
{"title":"某项目标书","doc_type":"标书","department":"售前部","industry":"政务"}
---
正文内容...
```

## 🧪 测试
```powershell
# 1) 单元测试（无需启动服务，使用临时目录隔离，共 48 项）
pip install -r requirements-dev.txt
pytest -q

# 2) 端到端测试（先启动服务，另开终端运行）
python scripts\smoke_test.py   # 覆盖 登录/多租户隔离/检索/问答/生成/导出/模板/审计
```
单元测试位于 `tests/`，覆盖：分块与元数据解析、Azure Mock 客户端、导出(Word/PDF)、
认证(令牌/口令)、章节模板、RAG 检索/生成/隔离、以及 API 集成（含 RBAC 与审计）。

## 💡 业务价值
- **提效**：标书初稿从数天缩短到分钟级，并可一键导出 Word/PDF 交付。
- **可信**：所有生成内容标注知识库来源，可追溯。
- **协同 + 隔离**：统一沉淀市场/售前/技术部知识资产，多租户安全隔离。

## 📚 文档
- [系统架构 ARCHITECTURE.md](ARCHITECTURE.md)（含 Mermaid 架构/时序/多租户图）
- [贡献指南 CONTRIBUTING.md](CONTRIBUTING.md)
- [pre-commit 钩子指南 docs/pre-commit.md](docs/pre-commit.md)
- [GitHub 仓库设置 docs/github-setup.md](docs/github-setup.md)（About / Topics）
- 英文文档：[README.en.md](README.en.md) · [ARCHITECTURE.en.md](ARCHITECTURE.en.md) · [CONTRIBUTING.en.md](CONTRIBUTING.en.md)

## 📄 License
[MIT](LICENSE)
