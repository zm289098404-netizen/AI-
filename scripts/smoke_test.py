import urllib.request, json, io
from urllib.parse import quote

BASE = "http://127.0.0.1:8000"

def req(method, path, body=None, token=None, raw=False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = BASE + quote(path, safe="/?=&:")
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
    except urllib.error.HTTPError as e:
        return e.code, (e.read() if raw else json.loads(e.read()))
    return resp.status, (resp.read() if raw else json.loads(resp.read()))

print("== health ==")
_, h = req("GET", "/api/health")
print(h)

print("\n== 401 without token ==")
code, _ = req("POST", "/api/ingest", token=None)
print("ingest no-token status:", code)

print("\n== login admin/demo ==")
_, lg = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
admin = lg["token"]
print("tenant:", lg["tenant_id"], "role:", lg["role"])

print("\n== ingest demo ==")
_, r = req("POST", "/api/ingest", {}, admin)
print("files:", r["files_processed"], "chunks:", r["chunks_indexed"], "backend:", r["backend"])

print("\n== stats demo ==")
_, s = req("GET", "/api/stats", token=admin)
print(s["total_chunks"], s["by_doc_type"], s["by_department"])

print("\n== search demo (banking) ==")
_, sr = req("POST", "/api/search", {"query": "银行 信创 国产化 数据库", "top_k": 3}, admin)
for hh in sr["hits"]:
    print("  -", hh["title"], "| score", hh["score"])

print("\n== ask demo ==")
_, a = req("POST", "/api/ask", {"question": "我们在金融行业有哪些案例和能力？"}, admin)
print("citations:", len(a["citations"]), "answer head:", a["answer"][:50])

print("\n== generate demo ==")
_, g = req("POST", "/api/generate",
           {"customer": "某城市商业银行", "industry": "金融",
            "requirements": "建设信创私有云，承载核心系统国产化迁移，满足等保四级与同城双活"}, admin)
print("title:", g["title"], "| citations:", len(g["citations"]))

print("\n== export docx/pdf ==")
code, docx_bytes = req("POST", "/api/export/docx", {"title": g["title"], "content": g["content"]}, admin, raw=True)
print("docx status:", code, "bytes:", len(docx_bytes), "magic:", docx_bytes[:2])
open("test_out.docx", "wb").write(docx_bytes)
code, pdf_bytes = req("POST", "/api/export/pdf", {"title": g["title"], "content": g["content"]}, admin, raw=True)
print("pdf status:", code, "bytes:", len(pdf_bytes), "magic:", pdf_bytes[:5])
open("test_out.pdf", "wb").write(pdf_bytes)

print("\n== tenant isolation: login acme ==")
_, lg2 = req("POST", "/api/auth/login", {"username": "acme", "password": "acme123"})
acme = lg2["token"]
req("POST", "/api/ingest", {}, acme)
_, s2 = req("GET", "/api/stats", token=acme)
print("acme stats:", s2["total_chunks"], s2["by_doc_type"])
_, sr2 = req("POST", "/api/search", {"query": "智能客服 零售", "top_k": 3}, acme)
print("acme top hits:", [x["title"] for x in sr2["hits"]])
# demo should NOT see acme docs
_, sr3 = req("POST", "/api/search", {"query": "智能客服 零售", "top_k": 3}, admin)
print("demo top hits (should be demo docs):", [x["title"] for x in sr3["hits"]])

print("\n== admin: list/create tenant + user ==")
_, tl = req("GET", "/api/admin/tenants", token=admin)
print("tenants:", [(t["id"], t["name"]) for t in tl])
code, ct = req("POST", "/api/admin/tenants", {"id": "beta", "name": "Beta 测试租户"}, admin)
print("create tenant status:", code, ct)
code, cu = req("POST", "/api/admin/users",
               {"username": "beta_user", "password": "beta123", "tenant_id": "beta", "role": "user"}, admin)
print("create user status:", code, "user:", cu.get("username"))

print("\n== non-admin forbidden ==")
_, lg3 = req("POST", "/api/auth/login", {"username": "presales", "password": "demo123"})
code, _ = req("GET", "/api/admin/tenants", token=lg3["token"])
print("presales access admin status (expect 403):", code)

print("\n== templates: list builtin ==")
_, tpls = req("GET", "/api/templates", token=admin)
print("template count:", len(tpls), "names:", [t["name"] for t in tpls])

print("\n== templates: create custom ==")
code, nt = req("POST", "/api/templates",
               {"name": "央企信创专项", "sections": ["需求理解", "信创适配方案", "案例佐证", "报价"]}, admin)
print("create status:", code, "id:", nt["id"][:8], "sections:", nt["sections"])

print("\n== generate with custom template ==")
_, g2 = req("POST", "/api/generate",
            {"customer": "某央企", "industry": "能源", "requirements": "信创替代，等保三级",
             "template_id": nt["id"]}, admin)
# 校验生成内容包含模板章节
has_secs = all(s in g2["content"] for s in nt["sections"])
print("title:", g2["title"], "| contains all template sections:", has_secs)

print("\n== generate with builtin template (POC) ==")
poc_id = next(t["id"] for t in tpls if "POC" in t["name"])
_, g3 = req("POST", "/api/generate",
            {"customer": "某客户", "industry": "制造", "requirements": "试点 MES",
             "template_id": poc_id}, admin)
print("POC contains 验收标准:", "验收标准与成功指标" in g3["content"])

print("\n== templates: delete custom ==")
code, _ = req("DELETE", "/api/templates/" + nt["id"], token=admin)
print("delete status:", code)
code, _ = req("DELETE", "/api/templates/builtin:标准投标方案", token=admin)
print("delete builtin (expect 400):", code)

print("\n== audit log ==")
_, al = req("GET", "/api/admin/audit?scope=tenant", token=admin)
actions = [e["action"] for e in al]
print("audit entries:", len(al))
print("recent actions:", actions[:8])
expected = {"login", "ingest", "generate", "export_docx", "create_template"}
print("covers key actions:", expected.issubset(set(actions)))

print("\nALL TESTS DONE")
