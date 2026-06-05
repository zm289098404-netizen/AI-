# Architecture

[中文](ARCHITECTURE.md) | **English**

This document describes the architecture, data flows, and key design decisions of the
Intelligent Bidding / Proposal Generation System.

## 1. Overall Architecture

```mermaid
flowchart TB
    subgraph Client["Browser Frontend (web/)"]
        UI["index.html + app.js<br/>Login / KB / Q&A / Generate / Templates / Admin"]
    end

    subgraph API["FastAPI Backend (app/main.py)"]
        AUTH["Auth dependencies<br/>get_current_user / require_admin"]
        ROUTES["Routes<br/>/api/auth /ingest /search /ask<br/>/generate /export /templates /admin"]
    end

    subgraph Core["Core modules (app/)"]
        AU["auth.py<br/>bcrypt + HMAC token"]
        TPL["templates_store.py<br/>section templates"]
        AUD["audit.py<br/>audit log"]
        EXP["export.py<br/>Word / PDF"]
    end

    subgraph RAG["RAG pipeline (app/rag/)"]
        ING["ingest.py<br/>parse + chunk"]
        RET["retriever.py<br/>backend abstraction"]
        GEN["generator.py<br/>Q&A + generation"]
        LLM["azure_client.py<br/>Azure OpenAI / Mock"]
    end

    subgraph Store["Storage"]
        CH[("ChromaDB<br/>vectors (per-tenant)")]
        AZ[("Azure AI Search<br/>hybrid (optional)")]
        DB[("SQLite app.db<br/>users/tenants/templates/audit")]
        FS[("Filesystem<br/>data/knowledge/&lt;tenant&gt;")]
    end

    UI -->|Bearer Token| ROUTES
    ROUTES --> AUTH
    AUTH --> AU
    ROUTES --> ING & RET & GEN & TPL & AUD & EXP
    ING --> RET
    GEN --> RET
    RET --> CH
    RET -.->|when configured| AZ
    ING --> LLM
    GEN --> LLM
    RET --> LLM
    AU --> DB
    TPL --> DB
    AUD --> DB
    ING --> FS
```

## 2. Retrieval-Augmented Generation (RAG) Data Flow

### 2.1 Ingest

```mermaid
sequenceDiagram
    participant U as User (admin)
    participant API as FastAPI
    participant ING as ingest.py
    participant LLM as azure_client
    participant BE as retriever backend
    participant DB as vector store

    U->>API: POST /api/ingest (Bearer)
    API->>ING: ingest_directory(tenant, reset=True)
    ING->>BE: reset(tenant)
    loop each document
        ING->>ING: parse(pdf/docx/md/txt) + chunk
        ING->>LLM: embed(chunks)
        LLM-->>ING: vectors (Azure or Mock)
        ING->>BE: index(tenant, ids, chunks, metas)
        BE->>DB: write vectors + metadata
    end
    ING-->>API: {files, chunks, backend}
    API-->>U: IngestResponse
```

### 2.2 Generate

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant TPL as templates_store
    participant GEN as generator.py
    participant BE as retriever backend
    participant LLM as azure_client
    participant AUD as audit.py

    U->>API: POST /api/generate (customer, requirements, template_id)
    API->>TPL: resolve_sections(tenant, template_id)
    TPL-->>API: section list
    API->>GEN: generate_bid(tenant, ..., sections)
    GEN->>BE: query(retrieve matching cases/products)
    BE->>LLM: embed(query)
    BE-->>GEN: hits + citations
    GEN->>LLM: chat(system, user, context)
    LLM-->>GEN: bid content (Azure or Mock placeholder)
    GEN-->>API: {title, content, citations}
    API->>AUD: log(generate)
    API-->>U: GenerateResponse
```

## 3. Multi-Tenant Isolation

```mermaid
flowchart LR
    subgraph demo["Tenant demo"]
        D1["collection: bid_knowledge_demo"]
        D2["data/knowledge/demo/"]
    end
    subgraph acme["Tenant acme"]
        A1["collection: bid_knowledge_acme"]
        A2["data/knowledge/acme/"]
    end
    JWT["HMAC token<br/>carries tenant_id"] --> Router
    Router{route by tenant_id} --> demo
    Router --> acme
```

- Each tenant has a **dedicated vector collection / index** and a **dedicated document directory**.
- The token carries `tenant_id`, which bounds all data access; users cannot read across tenants.

## 4. Pluggable Design

| Dimension | Default (zero-config) | When configured |
|-----------|----------------------|-----------------|
| LLM/Embedding | Mock (deterministic pseudo-vectors / placeholder text) | Azure OpenAI |
| Retrieval backend | ChromaDB (local persistence) | Azure AI Search (vector + keyword hybrid) |

Switching is decided automatically by `use_mock` / `use_azure_search` in `app/config.py`;
business code remains unchanged.

## 5. Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `app/config.py` | Env config; Mock/Azure detection; path management |
| `app/db.py` | Unified SQLite connection & schema init |
| `app/auth.py` | Users/tenants, bcrypt, HMAC tokens, FastAPI auth deps |
| `app/rag/azure_client.py` | Azure OpenAI wrapper + Mock fallback |
| `app/rag/store.py` | ChromaDB per-tenant isolation wrapper |
| `app/rag/retriever.py` | Retrieval backend abstraction (ChromaDB / Azure AI Search) |
| `app/rag/ingest.py` | Document parsing, chunking, indexing |
| `app/rag/generator.py` | Retrieval, Q&A, bid generation |
| `app/templates_store.py` | Section template CRUD |
| `app/audit.py` | Audit logging |
| `app/export.py` | Markdown → Word / PDF |

See the full API list in the [README](README.en.md#-api).
