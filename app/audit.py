"""操作审计日志：记录关键动作，供管理员查看。"""
import json
import time

from app.db import get_conn


def log(username: str, tenant_id: str, action: str, detail: dict | str = "") -> None:
    if isinstance(detail, dict):
        detail = json.dumps(detail, ensure_ascii=False)
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO audit_log(ts, username, tenant_id, action, detail) VALUES (?,?,?,?,?)",
                (time.time(), username, tenant_id, action, detail),
            )
    except Exception:
        # 审计失败不应影响主流程
        pass


def recent(tenant_id: str | None = None, limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        if tenant_id:
            rows = conn.execute(
                "SELECT ts, username, tenant_id, action, detail FROM audit_log "
                "WHERE tenant_id=? ORDER BY id DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, username, tenant_id, action, detail FROM audit_log "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "ts": r["ts"],
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
                "username": r["username"],
                "tenant_id": r["tenant_id"],
                "action": r["action"],
                "detail": r["detail"],
            }
        )
    return out
