const $ = (id) => document.getElementById(id);
let TOKEN = localStorage.getItem("bid_token") || "";
let USER = JSON.parse(localStorage.getItem("bid_user") || "null");
let LAST_BID = null; // {title, content}

function authHeaders(extra) {
  return Object.assign({ Authorization: "Bearer " + TOKEN }, extra || {});
}

async function api(path, opts = {}) {
  opts.headers = authHeaders(opts.headers);
  const r = await fetch(path, opts);
  if (r.status === 401) {
    doLogout();
    throw new Error("登录已过期，请重新登录");
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || ("请求失败 " + r.status));
  return data;
}

async function apiJson(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---------- 登录 ----------
$("btnLogin").onclick = login;
$("loginPass").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });

async function login() {
  $("loginError").textContent = "";
  try {
    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("loginUser").value.trim(), password: $("loginPass").value }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "登录失败");
    TOKEN = data.token;
    USER = data;
    localStorage.setItem("bid_token", TOKEN);
    localStorage.setItem("bid_user", JSON.stringify(USER));
    enterApp();
  } catch (e) {
    $("loginError").textContent = e.message;
  }
}

function doLogout() {
  TOKEN = ""; USER = null;
  localStorage.removeItem("bid_token");
  localStorage.removeItem("bid_user");
  $("appRoot").classList.add("hidden");
  $("loginOverlay").classList.remove("hidden");
}
$("btnLogout").onclick = doLogout;

function enterApp() {
  $("loginOverlay").classList.add("hidden");
  $("appRoot").classList.remove("hidden");
  $("userinfo").innerHTML = `👤 ${USER.display_name} <span class="role">${USER.role}</span>`;
  $("tenantTag").textContent = "租户：" + USER.tenant_id;
  document.querySelectorAll(".admin-only").forEach((el) =>
    el.classList.toggle("hidden", USER.role !== "admin")
  );
  loadStatus();
  loadTemplates();
}

// ---------- Tabs ----------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
    if (tab.dataset.tab === "admin") { loadTenants(); loadAudit(); loadModelConfig(); }
    if (tab.dataset.tab === "tpl") loadTemplates();
  };
});

// ---------- Markdown ----------
function renderMarkdown(md) {
  return md
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/^> (.*)$/gm, "<blockquote>$1</blockquote>")
    .replace(/^[-*] (.*)$/gm, "<li>$1</li>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n{2,}/g, "<br/><br/>")
    .replace(/\n/g, "<br/>");
}

function renderCitations(container, hits) {
  if (!hits || !hits.length) { container.innerHTML = '<p class="empty">无引用来源</p>'; return; }
  container.innerHTML =
    "<h3 style='font-size:14px;margin-bottom:8px'>引用来源</h3>" +
    hits.map((h, i) => `
      <div class="cite">
        <div class="meta">[来源${i + 1}] 《${h.title}》 · ${h.doc_type} / ${h.department} / ${h.industry}
          <span class="score">相似度 ${h.score}</span></div>
        <div class="txt">${h.text.slice(0, 220)}${h.text.length > 220 ? "…" : ""}</div>
      </div>`).join("");
}

// ---------- 状态/统计 ----------
async function loadStatus() {
  const h = await api("/api/health");
  const llm = h.mock_mode
    ? '<span class="badge mock">⚠ LLM:Mock</span>'
    : '<span class="badge live">● Azure OpenAI</span>';
  const be = h.azure_search
    ? '<span class="badge live">🔎 Azure AI Search(混合)</span>'
    : '<span class="badge gray">🔎 ChromaDB</span>';
  $("statusbar").innerHTML = llm + " " + be;
  await loadStats();
}

async function loadStats() {
  const s = await api("/api/stats");
  const dt = Object.entries(s.by_doc_type).map(([k, v]) => `${k}:${v}`).join("　") || "—";
  const dp = Object.entries(s.by_department).map(([k, v]) => `${k}:${v}`).join("　") || "—";
  $("kbStats").innerHTML = `
    <div class="stat-box"><div class="num">${s.total_chunks}</div><div class="lbl">知识片段总数</div></div>
    <div class="stat-box"><div class="lbl">按类型</div><div>${dt}</div></div>
    <div class="stat-box"><div class="lbl">按部门</div><div>${dp}</div></div>
    <div class="stat-box"><div class="lbl">检索后端</div><div>${s.backend}</div></div>`;
}

// ---------- 知识库 ----------
$("btnIngest").onclick = async () => {
  $("btnIngest").disabled = true;
  $("ingestLog").textContent = "正在解析文档并构建向量索引...";
  try {
    const r = await apiJson("/api/ingest", {});
    let log = `✅ 完成：处理文件 ${r.files_processed} 个，索引片段 ${r.chunks_indexed} 条（后端：${r.backend}）\n`;
    log += r.mock_mode ? "（LLM Mock 模式）\n\n" : "（Azure Embedding）\n\n";
    r.details.forEach((d) => { log += `• ${d.file} [${d.doc_type}] → ${d.chunks} 片段\n`; });
    $("ingestLog").textContent = log;
    await loadStats();
  } catch (e) { $("ingestLog").textContent = "❌ 失败：" + e.message; }
  $("btnIngest").disabled = false;
};

$("fileInput").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  $("ingestLog").textContent = `正在上传 ${file.name}...`;
  try {
    const r = await api("/api/upload", { method: "POST", body: fd });
    $("ingestLog").textContent = `✅ ${r.saved}\n${r.hint || ""}`;
  } catch (e) { $("ingestLog").textContent = "❌ " + e.message; }
};

// ---------- 问答 ----------
$("btnAsk").onclick = async () => {
  const q = $("askInput").value.trim();
  if (!q) return;
  $("askAnswer").innerHTML = '<span class="loading">思考中...</span>';
  $("askCitations").innerHTML = "";
  try {
    const r = await apiJson("/api/ask", {
      question: q, doc_type: $("askDocType").value || null, department: $("askDept").value || null,
    });
    $("askAnswer").innerHTML = renderMarkdown(r.answer);
    renderCitations($("askCitations"), r.citations);
  } catch (e) { $("askAnswer").textContent = "❌ " + e.message; }
};

// ---------- 标书生成 ----------
$("btnGen").onclick = async () => {
  const customer = $("genCustomer").value.trim();
  const req = $("genReq").value.trim();
  if (!customer || !req) { alert("请填写客户名称和 RFP 需求"); return; }
  $("btnGen").disabled = true;
  $("genResult").innerHTML = '<span class="loading">正在检索知识库并生成标书初稿...</span>';
  $("genCitations").innerHTML = "";
  $("btnExportDocx").classList.add("hidden");
  $("btnExportPdf").classList.add("hidden");
  try {
    const r = await apiJson("/api/generate", {
      customer, industry: $("genIndustry").value.trim(), requirements: req,
      template_id: $("genTemplate").value || null,
    });
    LAST_BID = { title: r.title, content: r.content };
    $("genResult").innerHTML = renderMarkdown(r.content);
    renderCitations($("genCitations"), r.citations);
    $("btnExportDocx").classList.remove("hidden");
    $("btnExportPdf").classList.remove("hidden");
  } catch (e) { $("genResult").textContent = "❌ 生成失败：" + e.message; }
  $("btnGen").disabled = false;
};

async function exportBid(fmt) {
  if (!LAST_BID) return;
  const r = await fetch("/api/export/" + fmt, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(LAST_BID),
  });
  if (!r.ok) { alert("导出失败"); return; }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = LAST_BID.title + (fmt === "docx" ? ".docx" : ".pdf");
  a.click();
  URL.revokeObjectURL(url);
}
$("btnExportDocx").onclick = () => exportBid("docx");
$("btnExportPdf").onclick = () => exportBid("pdf");

// ---------- 管理 ----------
async function loadTenants() {
  try {
    const list = await api("/api/admin/tenants");
    $("tenantList").innerHTML = list.map((t) =>
      `<span class="tenant-chip">${t.id} <small>${t.name}</small></span>`).join("");
  } catch (e) { $("tenantList").textContent = e.message; }
}

$("btnAddTenant").onclick = async () => {
  try {
    await apiJson("/api/admin/tenants", { id: $("newTenantId").value.trim(), name: $("newTenantName").value.trim() });
    $("newTenantId").value = ""; $("newTenantName").value = "";
    loadTenants();
  } catch (e) { alert(e.message); }
};

$("btnAddUser").onclick = async () => {
  $("adminLog").textContent = "创建中...";
  try {
    const r = await apiJson("/api/admin/users", {
      username: $("newUserName").value.trim(), password: $("newUserPass").value,
      tenant_id: $("newUserTenant").value.trim(), role: $("newUserRole").value,
    });
    $("adminLog").textContent = `✅ 已创建用户 ${r.username}（租户 ${r.tenant_id} / ${r.role}）`;
  } catch (e) { $("adminLog").textContent = "❌ " + e.message; }
};

// ---------- AI 模型配置 ----------
async function loadModelConfig() {
  try {
    const c = await api("/api/admin/model-config");
    $("modelMode").textContent = c.mock_mode
      ? "Mock（占位生成，不调用真实模型）"
      : "Azure OpenAI（真实调用）";
    $("modelMode").className = "mode-tag " + (c.mock_mode ? "mock" : "live");
    $("cfgMock").value = c.mock_mode_setting;
    $("cfgChat").value = c.chat_deployment;
    $("cfgEmbed").value = c.embedding_deployment;
    $("cfgTemp").value = c.temperature;
    $("chatPresets").innerHTML = c.chat_presets.map((p) => `<option value="${p}">`).join("");
    $("embedPresets").innerHTML = c.embedding_presets.map((p) => `<option value="${p}">`).join("");
    checkMockWarn(c);
    const ov = [];
    if (c.chat_overridden) ov.push("Chat");
    if (c.embedding_overridden) ov.push("Embedding");
    if (c.temperature_overridden) ov.push("温度");
    $("modelLog").textContent = ov.length
      ? `已覆盖默认值：${ov.join("、")}（默认 Chat=${c.chat_default}, Embedding=${c.embedding_default}）`
      : `当前使用 .env 默认值（Chat=${c.chat_default}, Embedding=${c.embedding_default}）`;
  } catch (e) { $("modelLog").textContent = "❌ " + e.message; }
}

let _hasCreds = false;
function checkMockWarn(c) {
  if (c && typeof c.has_credentials === "boolean") _hasCreds = c.has_credentials;
  const sel = $("cfgMock").value;
  if (sel === "off" && !_hasCreds) {
    $("modelWarn").textContent =
      "⚠️ 未配置 Azure 凭据（.env 中 ENDPOINT/API_KEY 为空），强制『真实』无法生效，系统仍将使用 Mock。请先在 .env 配置凭据。";
  } else if (sel === "on") {
    $("modelWarn").textContent = "ℹ️ 已强制 Mock 模式：生成为占位内容，不消耗 Azure 调用，适合离线演示。";
  } else {
    $("modelWarn").textContent = "";
  }
}
$("cfgMock").addEventListener("change", () => checkMockWarn());

function checkEmbedWarn() {
  // 切换 embedding 模型会改变向量维度，需重建索引
  const prev = $("modelWarn").textContent;
  const msg = "⚠️ 更换 Embedding 模型会改变向量维度，保存后请到『知识库』重建索引，否则检索将不准确。";
  if (!prev.includes("向量维度")) {
    $("modelWarn").textContent = (prev ? prev + " " : "") + msg;
  }
}
$("cfgEmbed").addEventListener("input", checkEmbedWarn);

$("btnSaveModel").onclick = async () => {
  $("modelLog").textContent = "保存中...";
  try {
    const body = {
      mock_mode: $("cfgMock").value,
      chat_deployment: $("cfgChat").value.trim() || null,
      embedding_deployment: $("cfgEmbed").value.trim() || null,
      temperature: $("cfgTemp").value === "" ? null : parseFloat($("cfgTemp").value),
    };
    await api("/api/admin/model-config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    $("modelLog").textContent = "✅ 已保存并生效";
    await loadModelConfig();
    await loadStatus();
  } catch (e) { $("modelLog").textContent = "❌ " + e.message; }
};

$("btnResetModel").onclick = async () => {
  if (!confirm("确认恢复为 .env 默认模型配置？")) return;
  try {
    await api("/api/admin/model-config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset: true }),
    });
    $("modelWarn").textContent = "";
    $("modelLog").textContent = "✅ 已恢复默认";
    await loadModelConfig();
  } catch (e) { $("modelLog").textContent = "❌ " + e.message; }
};

// ---------- 审计日志 ----------
$("btnRefreshAudit").onclick = loadAudit;
$("auditScope").onchange = loadAudit;

async function loadAudit() {
  try {
    const rows = await api("/api/admin/audit?scope=" + $("auditScope").value);
    if (!rows.length) { $("auditTable").innerHTML = '<p class="empty">暂无记录</p>'; return; }
    $("auditTable").innerHTML =
      '<table><thead><tr><th>时间</th><th>用户</th><th>租户</th><th>操作</th><th>详情</th></tr></thead><tbody>' +
      rows.map((r) =>
        `<tr><td>${r.time}</td><td>${r.username}</td><td>${r.tenant_id}</td>` +
        `<td><span class="act">${r.action}</span></td><td class="detail">${(r.detail || "").slice(0, 80)}</td></tr>`
      ).join("") + "</tbody></table>";
  } catch (e) { $("auditTable").textContent = e.message; }
}

// ---------- 章节模板 ----------
async function loadTemplates() {
  try {
    const list = await api("/api/templates");
    // 填充生成面板下拉
    const sel = $("genTemplate");
    sel.innerHTML = list.map((t) =>
      `<option value="${t.id}">${t.name}（${t.sections.length}章${t.builtin ? "·内置" : ""}）</option>`
    ).join("");
    // 填充模板管理列表
    if ($("tplList")) {
      $("tplList").innerHTML = list.map((t) => `
        <div class="tpl-card">
          <div class="tpl-head">
            <strong>${t.name}</strong>
            ${t.builtin ? '<span class="tpl-badge">内置</span>'
              : `<button class="tpl-del" data-id="${t.id}">删除</button>`}
          </div>
          <ol>${t.sections.map((s) => `<li>${s}</li>`).join("")}</ol>
        </div>`).join("");
      document.querySelectorAll(".tpl-del").forEach((b) => {
        b.onclick = async () => {
          if (!confirm("确认删除该模板？")) return;
          try { await api("/api/templates/" + encodeURIComponent(b.dataset.id), { method: "DELETE" }); loadTemplates(); }
          catch (e) { alert(e.message); }
        };
      });
    }
  } catch (e) { if ($("tplList")) $("tplList").textContent = e.message; }
}

$("btnAddTpl").onclick = async () => {
  const name = $("newTplName").value.trim();
  const sections = $("newTplSections").value.split("\n").map((s) => s.trim()).filter(Boolean);
  if (!name || !sections.length) { $("tplLog").textContent = "❌ 请填写名称和至少一个章节"; return; }
  try {
    await apiJson("/api/templates", { name, sections });
    $("tplLog").textContent = `✅ 已保存模板「${name}」（${sections.length} 章）`;
    $("newTplName").value = ""; $("newTplSections").value = "";
    loadTemplates();
  } catch (e) { $("tplLog").textContent = "❌ " + e.message; }
};

// ---------- 启动 ----------
if (TOKEN && USER) {
  enterApp();
} else {
  $("loginOverlay").classList.remove("hidden");
}
