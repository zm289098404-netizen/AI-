# Release Notes — v1.0.0

> 基于 RAG 的智能投标 / 方案生成系统 · 首个正式版本

## 🎯 项目简介
汇聚公司历年标书、成功案例与产品文档，构建 RAG 智能售前助手：快速检索知识、
带引用问答、一键生成结构化标书并导出 Word/PDF，显著缩短 RFP 响应周期、整合跨团队知识资产。

## ✨ 核心亮点
| 能力 | 说明 |
|------|------|
| 📚 知识库 | PDF/Word/MD/TXT 解析 + 中文分块 + 向量索引 |
| 🔎 检索 | 语义检索（ChromaDB）/ 可选 Azure AI Search 混合检索 |
| 💬 问答 | 检索增强 + 来源引用 |
| 📝 标书生成 | RFP → 检索匹配 → 多章节初稿（含引用） |
| 📐 章节模板 | 内置 3 套 + 租户自定义 CRUD |
| 📤 导出 | Word / PDF（中文字体内嵌） |
| 🔐 多租户 | 登录鉴权 + 按租户隔离知识库 |
| 🧾 审计 | 关键操作日志可查 |

## 🚀 快速开始
```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # 留空即 Mock 模式
python scripts/seed_data.py
uvicorn app.main:app --port 8000
```
访问 http://localhost:8000 ，演示账号 `admin / admin123`。

> 也可使用 Docker：`docker compose up --build`

## 🧱 技术栈
Python 3.11 · FastAPI · Azure OpenAI · ChromaDB / Azure AI Search · bcrypt + HMAC ·
python-docx + reportlab

## ✅ 质量保障
- 48 项 pytest 单元/集成测试
- GitHub Actions CI（单测 + 端到端 smoke test）
- pre-commit 钩子

## 📌 说明
- 无 Azure 凭据时自动以 Mock 模式运行，可完整演示流程。
- 生产部署请修改 `.env` 中的 `AUTH_SECRET`。

完整变更见 [CHANGELOG.md](CHANGELOG.md)。
