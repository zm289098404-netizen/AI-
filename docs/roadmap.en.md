# Roadmap & Enterprise Optimization Guide

> Evolution plan for "Beyondsoft · Intelligent Bidding / Proposal Generation System".
> 中文版：[roadmap.md](./roadmap.md)

## 1. What's already in v1.0

- ✅ Knowledge base: txt / md / pdf / docx parsing + Chinese-friendly chunking + vector indexing
- ✅ Retrieval: local ChromaDB + optional Azure AI Search hybrid search
- ✅ RAG Q&A and proposal generation with source citations
- ✅ Multi-tenant isolation, login, RBAC, audit logs
- ✅ One-click Word / PDF export (CJK font embedded)
- ✅ **20 industry templates** (collapsible by category) + tenant-custom templates
- ✅ Admin: AI model / Provider / API Key / Mock toggle / connection test / system settings
- ✅ Login page with Demo / Production deployment modes
- ✅ Docker image, CI, 80+ unit tests

## 2. Recommended hardening before production rollout

### 1. Security & compliance
- [ ] **Password hashing** with bcrypt / argon2id
- [ ] **JWT refresh token** + revocation list
- [ ] **Append-only audit log** + periodic archival
- [ ] **Rate limiting** (per IP / user), CSRF, CORS allow-list
- [ ] **AES-GCM encryption of API keys** in DB (currently plaintext)
- [ ] **PII / commercial-secret masking** on upload (ID / phone / bank / pricing)
- [ ] **Watermarked exports** with user + timestamp

### 2. Knowledge governance
- [ ] **Document versioning** with rollback
- [ ] **Review workflow**: upload → tag → review → publish
- [ ] **Rich metadata**: industry, client, year, deal size, win rate, tech stack
- [ ] **Duplicate / conflict detection**
- [ ] **Image / table extraction** from PDF
- [ ] **Expiration & retirement** by year or client status

### 3. RAG & generation quality
- [ ] **Hybrid retrieval + reranking** (BM25 + vector + cross-encoder)
- [ ] **Multi-query / HyDE rewriting** for higher recall
- [ ] **Per-section generation with citation alignment** (clickable jumps)
- [ ] **Controllable generation**: tone (formal/friendly), length (brief/standard/detailed)
- [ ] **Regenerate / continue / refine-by-section** actions
- [ ] **Streaming output (SSE)** for instant feedback
- [ ] **Prompt version management** with canary releases and A/B tests

### 4. Collaboration & workflow
- [ ] **Real-time multi-user editing** (CRDT / OT)
- [ ] **Review & comments** across pre-sales / tech / commercial
- [ ] **Task assignment**: break RFP into per-section assignments
- [ ] **Version diff** between revisions
- [ ] **Client tagging & pipeline stages**, integrated with CRM (Salesforce / DingTalk / Feishu)

### 5. User experience
- [ ] **Onboarding tour** (Upload → Index → Ask → Generate)
- [ ] **Drag-and-drop upload** with batch
- [ ] **Dark mode**
- [ ] **Keyboard shortcuts** (Ctrl+Enter, Ctrl+K)
- [ ] **History**: replay & favorite recent Q&A / generations
- [ ] **Citation hover cards** showing source snippet

### 6. Observability & operations
- [ ] **Metrics**: calls, token usage, latency, error rate
- [ ] **Cost dashboard** by user / tenant / model
- [ ] **Alerts** via WeCom / Feishu / email
- [ ] **Feedback loop** (👍 👎 + comments) to improve prompts and retrieval
- [ ] **A/B framework** comparing prompts / models against win rate

### 7. Deployment & scalability
- [ ] **PostgreSQL** in place of SQLite for concurrency and backups
- [ ] **MinIO / S3** object storage for raw documents
- [ ] **Redis cache** for common Q&A
- [ ] **Celery / RQ** for async large-file parsing & long generations
- [ ] **Kubernetes Helm chart** for on-prem deployment
- [ ] **SSO / SAML / OIDC** with corporate directory
- [ ] **Multi-region deployment** with load balancing

### 8. Advanced AI capabilities
- [ ] **Multimodal** chart / RFP screenshot understanding (CLIP / GPT-4V)
- [ ] **Agent orchestration**: auto-retrieve competitor pricing, call calc/search tools
- [ ] **Enterprise knowledge graph** linking projects-clients-tech-people
- [ ] **Local LLM support** (vLLM / Ollama / Wenxin / Qwen on-prem)
- [ ] **Fine-tuning / RLHF** with historical bids to match writing style

## 3. Commercialization suggestions

- Tiered editions: Community (OSS) / Pro (private deploy) / Enterprise (SSO + advanced security)
- Integrations with CRM / ERP / contract management
- Template marketplace by industry (government, finance, manufacturing, healthcare …)
- Training & service packs (prompt engineering, KB bootstrapping)

---

> This roadmap is iterative. Issues and PRs welcome on GitHub.
