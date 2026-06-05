# GitHub 仓库设置参考 (About & Topics)

**中文** | [English](github-setup.en.md)

本文件记录仓库的推荐简介(About)与主题标签(Topics)，便于日后参考或迁移。

## 仓库简介 (Description)

精简版（推荐，避免超长）：
```
RAG 智能投标/方案生成助手 · FastAPI + Azure OpenAI + ChromaDB · 多租户 · Word/PDF 导出
```

中文完整版：
```
基于 RAG 的智能投标/方案生成系统：知识库检索、智能问答、一键生成标书并导出 Word/PDF；支持多租户、章节模板与审计。FastAPI + Azure OpenAI + ChromaDB。
```

英文版：
```
RAG-based intelligent bidding/proposal assistant: knowledge retrieval, cited Q&A, one-click bid generation with Word/PDF export. Multi-tenant, templates & audit. FastAPI + Azure OpenAI + ChromaDB.
```

## 主题标签 (Topics)

```
rag  llm  azure-openai  fastapi  chromadb  retrieval-augmented-generation
python  vector-search  semantic-search  presales  proposal-generator
multi-tenant  bidding  knowledge-base  ai-assistant  document-generation  chinese-nlp
```

## 设置方式

### 方式 A：网页
1. 打开仓库主页 → 右上角 About 区域点 ⚙️ 齿轮
2. Description 粘贴上面的简介
3. Topics 逐个输入标签（每个回车确认）
4. Save changes

### 方式 B：GitHub CLI（一键）
先安装 [GitHub CLI](https://cli.github.com/) 并 `gh auth login`，然后运行本仓库的脚本：
```powershell
.\setup-repo-meta.ps1
```
或手动执行：
```powershell
gh repo edit zm289098404-netizen/AI- --description "RAG 智能投标/方案生成助手 · FastAPI + Azure OpenAI + ChromaDB · 多租户 · Word/PDF 导出"

gh repo edit zm289098404-netizen/AI- --add-topic rag,llm,azure-openai,fastapi,chromadb,retrieval-augmented-generation,python,vector-search,semantic-search,presales,proposal-generator,multi-tenant,bidding,knowledge-base,ai-assistant,document-generation,chinese-nlp
```

## 其他建议
- **Social preview**：Settings → General → Social preview，上传 `docs/assets/cover.png`。
- **Website**：可填部署地址，本地演示可留空或填 `http://localhost:8000`。
