"""标书章节模板：内置默认 + 租户自定义（CRUD）。"""
import json
import time
import uuid
from typing import Optional

from fastapi import HTTPException

from app.db import get_conn
from app.rag.generator import DEFAULT_SECTIONS

BUILTIN_TEMPLATES = {
    "标准投标方案": DEFAULT_SECTIONS,
    "技术方案（精简）": [
        "需求理解",
        "技术架构与方案",
        "关键技术与优势",
        "实施与交付计划",
    ],
    "POC/试点方案": [
        "试点目标与范围",
        "方案设计",
        "实施步骤",
        "验收标准与成功指标",
    ],
}


def _row_to_template(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "sections": json.loads(row["sections"]),
        "builtin": False,
    }


def list_templates(tenant_id: str) -> list[dict]:
    items = [
        {"id": f"builtin:{name}", "name": name, "sections": secs, "builtin": True}
        for name, secs in BUILTIN_TEMPLATES.items()
    ]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM templates WHERE tenant_id=? ORDER BY created_at", (tenant_id,)
        ).fetchall()
    items.extend(_row_to_template(r) for r in rows)
    return items


def create_template(tenant_id: str, name: str, sections: list[str]) -> dict:
    name = name.strip()
    sections = [s.strip() for s in sections if s.strip()]
    if not name:
        raise HTTPException(400, "模板名称不能为空")
    if not sections:
        raise HTTPException(400, "至少需要一个章节")
    if name in BUILTIN_TEMPLATES:
        raise HTTPException(409, "模板名与内置模板冲突，请改名")
    tid = str(uuid.uuid4())
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO templates(id, tenant_id, name, sections, created_at) VALUES (?,?,?,?,?)",
                (tid, tenant_id, name, json.dumps(sections, ensure_ascii=False), time.time()),
            )
        except Exception:
            raise HTTPException(409, f"模板已存在: {name}")
    return {"id": tid, "name": name, "sections": sections, "builtin": False}


def delete_template(tenant_id: str, template_id: str) -> None:
    if template_id.startswith("builtin:"):
        raise HTTPException(400, "内置模板不可删除")
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM templates WHERE id=? AND tenant_id=?", (template_id, tenant_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "模板不存在")


def resolve_sections(tenant_id: str, template_id: Optional[str]) -> Optional[list[str]]:
    """根据模板 id 返回章节列表；None 表示使用默认。"""
    if not template_id:
        return None
    if template_id.startswith("builtin:"):
        name = template_id.split(":", 1)[1]
        return BUILTIN_TEMPLATES.get(name)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sections FROM templates WHERE id=? AND tenant_id=?",
            (template_id, tenant_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "模板不存在或无权访问")
    return json.loads(row["sections"])
