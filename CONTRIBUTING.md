# 贡献指南 (Contributing)

**中文** | [English](CONTRIBUTING.en.md)

感谢你对本项目的关注！

## 开发环境
- Python 3.11
- 安装依赖：`pip install -r requirements-dev.txt`（含 pytest）
- 复制配置：`cp .env.example .env`（不配置 Azure 凭据即以 Mock 模式运行）

## 本地运行
```bash
python scripts/seed_data.py          # 生成示例知识库
uvicorn app.main:app --reload --port 8000
```

## 提交前自检
- 运行单元测试：`pytest -q`（48 项，使用临时目录隔离，无需启动服务）
- 启动服务后运行端到端测试：`python scripts/smoke_test.py`
- 确保不要提交以下内容（已在 .gitignore 中忽略）：
  - `.env`（真实凭据）
  - `data/chroma/`、`data/app.db`（运行时数据）
  - `data/knowledge/`（由 seed 脚本生成，或为客户私有文档）

## pre-commit 钩子（推荐）
本仓库提供 `.pre-commit-config.yaml`，在每次提交前自动运行：清理尾随空格、
校验 YAML/JSON、检测私钥、并运行 pytest 单元测试。

```bash
pip install pre-commit
pre-commit install            # 安装 git 钩子
pre-commit run --all-files    # 可选：对全部文件手动跑一次
```
安装后，`git commit` 会自动触发检查；任一检查失败将阻止提交。
详见 [docs/pre-commit.md](docs/pre-commit.md)。

## 代码风格
- 后端遵循 PEP 8；保持函数小而清晰。
- 提交信息使用简洁的中文或英文祈使句。

## 安全
- 切勿提交任何密钥、口令或客户真实标书数据。
- 生产部署请修改 `.env` 中的 `AUTH_SECRET`。
