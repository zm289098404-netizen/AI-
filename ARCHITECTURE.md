# 系统架构 (Architecture)

**中文** | [English](ARCHITECTURE.en.md)

本文档描述智能投标/方案生成系统的架构、数据流与关键设计。

## 1. 总体架构

```mermaid
flowchart TB
    subgraph Client["浏览器前端 (web/)"]
        UI["index.html + app.js<br/>登录 / 知识库 / 问答 / 生成 / 模板 / 管理"]
    end

    subgraph API["FastAPI 后端 (app/main.py)"]
        AUTH["认证依赖<br/>get_current_user / require_admin"]
        ROUTES["路由层<br/>/api/auth /ingest /search /ask<br/>/generate /export /templates /admin"]
    end

    subgraph Core["核心模块 (app/)"]
        AU["auth.py<br/>bcrypt + HMAC 令牌"]
        TPL["templates_store.py<br/>章节模板"]
        AUD["audit.py<br/>审计日志"]
        EXP["export.py<br/>Word / PDF"]
    end

    subgraph RAG["RAG 管线 (app/rag/)"]
        ING["ingest.py<br/>解析 + 分块"]
        RET["retriever.py<br/>后端抽象"]
        GEN["generator.py<br/>问答 + 生成"]
        LLM["azure_client.py<br/>Azure OpenAI / Mock"]
    end

    subgraph Store["存储"]
        CH[("ChromaDB<br/>向量(按租户)")]
        AZ[("Azure AI Search<br/>混合检索(可选)")]
        DB[("SQLite app.db<br/>用户/租户/模板/审计")]
        FS[("文件系统<br/>data/knowledge/&lt;tenant&gt;")]
    end

    UI -->|Bearer Token| ROUTES
    ROUTES --> AUTH
    AUTH --> AU
    ROUTES --> ING & RET & GEN & TPL & AUD & EXP
    ING --> RET
    GEN --> RET
    RET --> CH
    RET -.->|配置后| AZ
    ING --> LLM
    GEN --> LLM
    RET --> LLM
    AU --> DB
    TPL --> DB
    AUD --> DB
    ING --> FS
```

## 2. 检索增强生成 (RAG) 数据流

### 2.1 知识入库 (Ingest)

```mermaid
sequenceDiagram
    participant U as 用户(管理员)
    participant API as FastAPI
    participant ING as ingest.py
    participant LLM as azure_client
    participant BE as retriever 后端
    participant DB as 向量库

    U->>API: POST /api/ingest (Bearer)
    API->>ING: ingest_directory(tenant, reset=True)
    ING->>BE: reset(tenant)
    loop 每个文档
        ING->>ING: 解析(pdf/docx/md/txt) + 分块
        ING->>LLM: embed(chunks)
        LLM-->>ING: 向量 (Azure 或 Mock)
        ING->>BE: index(tenant, ids, chunks, metas)
        BE->>DB: 写入向量 + 元数据
    end
    ING-->>API: {files, chunks, backend}
    API-->>U: IngestResponse
```

### 2.2 标书生成 (Generate)

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as FastAPI
    participant TPL as templates_store
    participant GEN as generator.py
    participant BE as retriever 后端
    participant LLM as azure_client
    participant AUD as audit.py

    U->>API: POST /api/generate (customer, requirements, template_id)
    API->>TPL: resolve_sections(tenant, template_id)
    TPL-->>API: 章节列表
    API->>GEN: generate_bid(tenant, ..., sections)
    GEN->>BE: query(检索匹配案例/产品)
    BE->>LLM: embed(query)
    BE-->>GEN: 命中片段 + 引用
    GEN->>LLM: chat(system, user, context)
    LLM-->>GEN: 标书正文 (Azure 或 Mock 占位)
    GEN-->>API: {title, content, citations}
    API->>AUD: log(generate)
    API-->>U: GenerateResponse
```

## 3. 多租户隔离

```mermaid
flowchart LR
    subgraph demo["租户 demo"]
        D1["collection: bid_knowledge_demo"]
        D2["data/knowledge/demo/"]
    end
    subgraph acme["租户 acme"]
        A1["collection: bid_knowledge_acme"]
        A2["data/knowledge/acme/"]
    end
    JWT["HMAC 令牌<br/>携带 tenant_id"] --> Router
    Router{路由按 tenant_id 路由} --> demo
    Router --> acme
```

- 每个租户拥有**独立向量 collection / 索引**与**独立文档目录**。
- 令牌内含 `tenant_id`，所有数据访问以此为边界；用户无法跨租户读取。

## 4. 可插拔设计

| 维度 | 默认（零配置） | 配置后 |
|------|----------------|--------|
| LLM/Embedding | Mock（确定性伪向量/占位文本） | Azure OpenAI |
| 检索后端 | ChromaDB（本地持久化） | Azure AI Search（向量+关键词混合） |

切换由 `app/config.py` 的 `use_mock` / `use_azure_search` 自动判定，业务代码无需改动。

## 5. 关键模块职责

| 模块 | 职责 |
|------|------|
| `app/config.py` | 环境配置；Mock/Azure 判定；路径管理 |
| `app/db.py` | 统一 SQLite 连接与建表 |
| `app/auth.py` | 用户/租户、bcrypt、HMAC 令牌、FastAPI 鉴权依赖 |
| `app/rag/azure_client.py` | Azure OpenAI 封装 + Mock 降级 |
| `app/rag/store.py` | ChromaDB 按租户隔离封装 |
| `app/rag/retriever.py` | 检索后端抽象（ChromaDB / Azure AI Search） |
| `app/rag/ingest.py` | 文档解析、分块、入库 |
| `app/rag/generator.py` | 检索、问答、标书生成 |
| `app/templates_store.py` | 章节模板 CRUD |
| `app/settings_store.py` | 运行时 AI 模型配置（管理端切换） |
| `app/audit.py` | 操作审计日志 |
| `app/export.py` | Markdown → Word / PDF |

完整 API 列表见 [README](README.md#-api)。
