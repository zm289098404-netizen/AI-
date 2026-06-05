"""检索 + RAG 生成：智能问答与标书/方案生成（按租户）。"""
from app.config import settings
from app.rag.retriever import get_backend
from app.rag.azure_client import get_llm


def search(tenant_id, query, top_k=None, doc_type=None, department=None) -> list[dict]:
    k = top_k or settings.top_k
    return get_backend().query(
        tenant_id, query, k, doc_type=doc_type, department=department
    )


def _format_context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(
            f"[来源{i}] 《{h['title']}》（类型:{h['doc_type']} 部门:{h['department']} "
            f"行业:{h['industry']}）\n{h['text']}"
        )
    return "\n\n".join(blocks)


def ask(tenant_id, question, top_k=None, doc_type=None, department=None) -> dict:
    hits = search(
        tenant_id, question, top_k=top_k, doc_type=doc_type, department=department
    )
    context = _format_context(hits)
    system = (
        "你是公司的智能售前助手。请严格依据提供的知识库片段回答用户问题，"
        "回答要专业、准确、条理清晰，并在引用事实处标注来源编号（如 [来源1]）。"
        "若知识库中没有相关信息，请明确说明，不要编造。"
    )
    user = f"知识库片段：\n{context}\n\n用户问题：{question}\n\n请给出带来源标注的回答。"
    answer = get_llm().chat(system, user, context=context)
    return {"answer": answer, "citations": hits, "mock_mode": settings.use_mock}


DEFAULT_SECTIONS = [
    "项目背景与需求理解",
    "总体技术方案",
    "实施计划与里程碑",
    "成功案例佐证",
    "产品与能力优势",
    "服务与保障体系",
    "报价框架",
]


def generate_bid(
    tenant_id,
    customer: str,
    industry: str,
    requirements: str,
    sections=None,
    top_k=None,
) -> dict:
    sections = sections or DEFAULT_SECTIONS
    retrieval_query = f"{industry} {requirements} 解决方案 案例 产品"
    hits = search(tenant_id, retrieval_query, top_k=top_k or max(settings.top_k, 6))
    context = _format_context(hits)

    section_list = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sections))
    system = (
        "你是资深售前方案专家。请基于公司知识库（历史标书、成功案例、产品文档）"
        "为客户撰写一份专业的投标方案初稿。要求：结构完整、语言正式、突出公司优势、"
        "在引用案例或产品能力时标注来源编号（如 [来源1]）；如某章节缺乏依据，"
        "请基于通用最佳实践给出合理内容并提示需补充。"
    )
    user = (
        f"客户名称：{customer}\n行业：{industry or '未指定'}\n\n"
        f"客户需求/RFP 要点：\n{requirements}\n\n"
        f"请按以下章节结构输出 Markdown 格式的标书初稿：\n{section_list}\n\n"
        f"可参考的知识库片段：\n{context}"
    )
    content = get_llm().chat(system, user, context=context)

    if settings.use_mock:
        content = _mock_bid(customer, industry, requirements, sections, hits)

    title = f"{customer}{('（' + industry + '行业）') if industry else ''}投标方案"
    return {
        "title": title,
        "content": content,
        "citations": hits,
        "mock_mode": settings.use_mock,
    }


def _mock_bid(customer, industry, requirements, sections, hits) -> str:
    lines = [f"# {customer}投标方案（初稿）", ""]
    lines.append(
        "> 【Mock 模式】未配置 Azure OpenAI 凭据，以下为基于知识库检索的结构化占位初稿。"
        "配置真实凭据后将由大模型生成完整内容。\n"
    )
    lines.append(f"**客户**：{customer}　**行业**：{industry or '通用'}\n")
    lines.append(f"**需求摘要**：{requirements}\n")
    ref_map = {i + 1: h for i, h in enumerate(hits)}
    for idx, sec in enumerate(sections, 1):
        lines.append(f"\n## {idx}. {sec}")
        if hits:
            h = hits[(idx - 1) % len(hits)]
            lines.append(
                f"（参考 [来源{(idx - 1) % len(hits) + 1}]《{h['title']}》）\n\n{h['text'][:300]}…"
            )
        else:
            lines.append("（知识库暂无相关片段，请补充资料。）")
    if hits:
        lines.append("\n## 引用来源")
        for i, h in ref_map.items():
            lines.append(f"- [来源{i}]《{h['title']}》（{h['doc_type']}/{h['department']}）")
    return "\n".join(lines)
