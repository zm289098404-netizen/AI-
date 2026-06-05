"""标书章节模板：内置默认 + 租户自定义（CRUD）。"""
import json
import time
import uuid
from typing import Optional

from fastapi import HTTPException

from app.db import get_conn
from app.rag.generator import DEFAULT_SECTIONS

# 20 套内置章节模板，按行业/类别分组，便于折叠展示与检索。
# 每条 = (name, category, sections)
BUILTIN_TEMPLATE_LIST: list[dict] = [
    # —— 通用 ——
    {"name": "标准投标方案", "category": "通用",
     "sections": DEFAULT_SECTIONS},
    {"name": "技术方案（精简）", "category": "通用",
     "sections": ["需求理解", "技术架构与方案", "关键技术与优势", "实施与交付计划"]},
    {"name": "POC / 试点方案", "category": "通用",
     "sections": ["试点目标与范围", "方案设计", "实施步骤", "验收标准与成功指标"]},

    # —— 政务 / 政企 ——
    {"name": "政务大数据中台方案", "category": "政务·政企",
     "sections": ["项目背景与政策依据", "现状与痛点分析", "数据中台总体架构",
                  "信创适配与等保合规", "实施计划与里程碑", "运营服务体系", "报价框架"]},
    {"name": "智慧城市 / 智慧园区方案", "category": "政务·政企",
     "sections": ["建设背景与愿景", "总体规划与分层架构", "感知与物联接入",
                  "城市大脑 / 应用场景", "数据共享与运营机制", "三年实施路线图", "投资概算"]},

    # —— 金融 ——
    {"name": "银行信创云平台方案", "category": "金融",
     "sections": ["监管要求与信创背景", "目标架构与选型说明", "迁移与改造方案",
                  "高可用与容灾", "安全合规（等保/密评）", "实施与试点计划", "TCO 与报价"]},
    {"name": "金融科技 / 数字银行方案", "category": "金融",
     "sections": ["业务诉求与场景梳理", "数字化总体方案", "核心系统能力增强",
                  "数据驱动与智能营销", "合规与风控", "敏捷交付计划", "商务报价"]},

    # —— 制造 / 工业 ——
    {"name": "智能制造 / MES 方案", "category": "制造·工业",
     "sections": ["工厂现状与诊断", "MES 总体方案", "产线数据采集与互联",
                  "排产与质量追溯", "与 ERP / PLM 集成", "实施计划与培训", "报价框架"]},
    {"name": "工业互联网平台方案", "category": "制造·工业",
     "sections": ["行业洞察与机会点", "平台分层架构", "工业 APP 与场景",
                  "设备接入与边缘计算", "数据资产与算法", "生态与合作模式", "投资与回报"]},

    # —— 互联网 / AI / 数据 ——
    {"name": "大模型 / 生成式 AI 应用平台方案", "category": "互联网·AI",
     "sections": ["业务场景与价值预估", "模型选型与对比", "RAG 知识工程方案",
                  "Agent 与编排能力", "安全/可控/审计", "POC 与上线计划", "成本与商务"]},
    {"name": "数据中台 / BI 分析方案", "category": "互联网·AI",
     "sections": ["数据现状评估", "中台与指标体系", "数据治理与质量",
                  "可视化与自助分析", "业务赋能场景", "实施路线图", "报价框架"]},
    {"name": "SaaS / PaaS 平台方案", "category": "互联网·AI",
     "sections": ["产品定位与差异化", "多租户架构设计", "扩展性与计费体系",
                  "运营与客户成功", "安全合规", "上线节奏与里程碑", "订阅报价模型"]},

    # —— 行业应用 ——
    {"name": "智能客服 / 知识助手方案", "category": "行业应用",
     "sections": ["业务现状与改进点", "智能客服总体方案", "知识库与 RAG 检索",
                  "多渠道接入", "效果评估与持续优化", "实施计划", "报价框架"]},
    {"name": "智慧医疗信息化方案", "category": "行业应用",
     "sections": ["医院信息化现状", "总体规划与架构", "电子病历与互联互通",
                  "医疗 AI 辅助应用", "数据安全与合规", "分期实施计划", "报价与服务"]},
    {"name": "智慧教育 / 在线学习平台方案", "category": "行业应用",
     "sections": ["教学痛点与目标", "平台总体方案", "教学资源与教研管理",
                  "AI 个性化学习", "运营与师资支持", "建设里程碑", "投资概算"]},
    {"name": "智慧能源 / 电力数字化方案", "category": "行业应用",
     "sections": ["业务背景与监管要求", "总体技术方案", "源-网-荷-储统一调度",
                  "AI 预测与运维优化", "安全防护与等保", "实施计划", "报价框架"]},

    # —— 安全 / 运维 ——
    {"name": "网络安全 / 等保合规方案", "category": "安全·运维",
     "sections": ["合规背景与差距分析", "纵深防御总体方案", "安全产品与服务清单",
                  "应急响应与演练", "合规测评配合", "实施计划", "服务报价"]},
    {"name": "DevOps / 研发效能提升方案", "category": "安全·运维",
     "sections": ["研发现状评估", "DevOps 工具链与流程", "CI/CD 与自动化测试",
                  "度量体系与改进闭环", "组织变革与培训", "落地路线图", "服务报价"]},

    # —— 服务交付 ——
    {"name": "软件外包 / 驻场服务方案", "category": "服务交付",
     "sections": ["客户需求理解", "团队与角色配置", "项目管理与交付流程",
                  "质量与风险控制", "知识沉淀与转移", "服务承诺 SLA", "人天报价框架"]},
    {"name": "测试外包 / 质量保障方案", "category": "服务交付",
     "sections": ["测试现状与诉求", "测试服务总体方案", "自动化与性能测试",
                  "缺陷管理与度量", "团队配置与梯队", "实施计划", "报价与计费方式"]},
]

# 兼容旧字典访问方式（按名称查 sections）
BUILTIN_TEMPLATES: dict[str, list[str]] = {t["name"]: t["sections"] for t in BUILTIN_TEMPLATE_LIST}
BUILTIN_CATEGORIES: list[str] = list(dict.fromkeys(t["category"] for t in BUILTIN_TEMPLATE_LIST))


def _row_to_template(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": "自定义",
        "sections": json.loads(row["sections"]),
        "builtin": False,
    }


def list_templates(tenant_id: str) -> list[dict]:
    items = [
        {"id": f"builtin:{t['name']}", "name": t["name"], "category": t["category"],
         "sections": t["sections"], "builtin": True}
        for t in BUILTIN_TEMPLATE_LIST
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
