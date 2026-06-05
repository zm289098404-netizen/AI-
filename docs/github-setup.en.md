# GitHub Repository Setup Reference (About & Topics)

[中文](github-setup.md) | **English**

This file records the recommended repository description (About) and topics, for future reference or migration.

## Description

Compact (recommended, avoids truncation):
```
RAG 智能投标/方案生成助手 · FastAPI + Azure OpenAI + ChromaDB · 多租户 · Word/PDF 导出
```

English:
```
RAG-based intelligent bidding/proposal assistant: knowledge retrieval, cited Q&A, one-click bid generation with Word/PDF export. Multi-tenant, templates & audit. FastAPI + Azure OpenAI + ChromaDB.
```

## Topics

```
rag  llm  azure-openai  fastapi  chromadb  retrieval-augmented-generation
python  vector-search  semantic-search  presales  proposal-generator
multi-tenant  bidding  knowledge-base  ai-assistant  document-generation  chinese-nlp
```

## How to Set

### Option A: Web UI
1. Open the repo home page → click the ⚙️ gear in the About section
2. Paste the description into Description
3. Enter topics one by one (press Enter for each)
4. Save changes

### Option B: GitHub CLI (one-click)
Install [GitHub CLI](https://cli.github.com/), run `gh auth login`, then run the script in this repo:
```powershell
.\setup-repo-meta.ps1
```
Or manually:
```powershell
gh repo edit zm289098404-netizen/AI- --description "RAG-based intelligent bidding/proposal assistant. FastAPI + Azure OpenAI + ChromaDB. Multi-tenant, Word/PDF export."

gh repo edit zm289098404-netizen/AI- --add-topic rag,llm,azure-openai,fastapi,chromadb,retrieval-augmented-generation,python,vector-search,semantic-search,presales,proposal-generator,multi-tenant,bidding,knowledge-base,ai-assistant,document-generation,chinese-nlp
```

## Other Tips
- **Social preview**: Settings → General → Social preview, upload `docs/assets/cover.png`.
- **Website**: set your deployment URL, or leave empty / use `http://localhost:8000` for local demos.
