# 贡献指南 (Contributing)

感谢你对本项目的关注！

## 开发环境
- Python 3.11
- 安装依赖：`pip install -r requirements.txt`
- 复制配置：`cp .env.example .env`（不配置 Azure 凭据即以 Mock 模式运行）

## 本地运行
```bash
python scripts/seed_data.py          # 生成示例知识库
uvicorn app.main:app --reload --port 8000
```

## 提交前自检
- 启动服务后运行端到端测试：`python scripts/smoke_test.py`
- 确保不要提交以下内容（已在 .gitignore 中忽略）：
  - `.env`（真实凭据）
  - `data/chroma/`、`data/app.db`（运行时数据）
  - `data/knowledge/`（由 seed 脚本生成，或为客户私有文档）

## 代码风格
- 后端遵循 PEP 8；保持函数小而清晰。
- 提交信息使用简洁的中文或英文祈使句。

## 安全
- 切勿提交任何密钥、口令或客户真实标书数据。
- 生产部署请修改 `.env` 中的 `AUTH_SECRET`。
