# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-06-06

首个正式版本。基于 RAG 的智能投标/方案生成系统，覆盖从知识库构建到标书生成、导出的完整售前流程。

### ✨ 功能 (Features)
- **知识库构建**：解析 PDF / Word / Markdown / TXT，中文友好分块，向量化入库。
- **语义 / 混合检索**：按文档类型（标书/案例/产品）、部门过滤；可选 Azure AI Search 混合检索。
- **智能问答**：检索增强 + 带来源引用的回答。
- **标书生成**：输入 RFP 需求，检索匹配案例/产品，生成多章节标书初稿（含引用）。
- **自定义章节模板**：内置 3 套 + 租户级自定义模板（CRUD）。
- **一键导出**：标书导出为 Word(.docx) / PDF（中文字体内嵌）。
- **登录 + 多租户**：账号体系 + 按租户隔离的知识库（数据互不可见）。
- **操作审计日志**：记录登录/入库/生成/导出/管理等关键动作。
- **Azure OpenAI 集成**：无凭据时自动降级 Mock 模式，开箱即用。

### 🏗️ 工程 (Engineering)
- FastAPI 后端 + 原生 Web 前端（登录/知识库/问答/生成/模板/管理六大面板）。
- 检索后端抽象：ChromaDB（本地）/ Azure AI Search（混合）可插拔。
- 认证：bcrypt 口令 + HMAC 签名令牌。
- 48 项 pytest 单元/集成测试，临时目录隔离。
- Docker / docker-compose、一键启动脚本、GitHub Actions CI。
- pre-commit 钩子（尾空格/YAML/JSON/私钥检测 + pytest）。

### 📚 文档 (Docs)
- 中英双语 README、ARCHITECTURE（含 Mermaid 图）、CONTRIBUTING、pre-commit、github-setup。
- 项目封面图（SVG + PNG）。

[1.0.0]: https://github.com/zm289098404-netizen/AI-/releases/tag/v1.0.0
