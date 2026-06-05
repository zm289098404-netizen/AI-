const $ = (id) => document.getElementById(id);
let TOKEN = localStorage.getItem("bid_token") || "";
let USER = JSON.parse(localStorage.getItem("bid_user") || "null");
let LAST_BID = null;
let PROVIDER_PRESETS = [];
let SYSTEM_INFO = null;
let TEMPLATES_CACHE = [];

// ============== Toast ==============
function toast(msg, kind) {
  const t = document.createElement("div");
  t.className = "toast " + (kind || "");
  t.textContent = msg;
  $("toastRoot").appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 2600);
  setTimeout(() => t.remove(), 3000);
}

// ============== HTTP ==============
function authHeaders(extra) {
  return Object.assign({ Authorization: "Bearer " + TOKEN }, extra || {});
}
async function api(path, opts = {}) {
  opts.headers = authHeaders(opts.headers);
  const r = await fetch(path, opts);
  if (r.status === 401) { doLogout(); throw new Error("登录已过期，请重新登录"); }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || ("请求失败 " + r.status));
  return data;
}
async function apiJson(path, body) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

// ============== 登录页 ==============
async function loadPublicSystemInfo() {
  try {
    const info = await fetch("/api/system").then((r) => r.json());
    SYSTEM_INFO = info;
    $("loginBrand").textContent = info.brand_name;
    $("appBrand").textContent = info.brand_name;
    document.title = info.brand_name;
    setLoginMode(info.deployment_mode === "production" ? "production" : "demo", false);
    const tags = [];
    tags.push(info.deployment_mode === "production" ? "🚀 正式部署" : "🎮 演示模式");
    tags.push(info.mock_mode ? "Mock" : "Live AI");
    tags.push(info.backend);
    $("loginSystemInfo").textContent = tags.join(" · ");
  } catch (e) { /* keep defaults */ }
}

function setLoginMode(mode, fromUser) {
  document.querySelectorAll(".login-tab").forEach((b) =>
    b.classList.toggle("active", b.dataset.mode === mode)
  );
  const isProd = mode === "production";
  $("loginDemoBox").classList.toggle("hidden", isProd);
  $("loginProdBox").classList.toggle("hidden", !isProd);
  if (fromUser) {
    // 用户切换 Tab 时如果当前 SYSTEM_INFO 与之不符，给出温和提示，不强制改后端
    if (SYSTEM_INFO && SYSTEM_INFO.deployment_mode !== mode) {
      $("loginError").textContent =
        mode === "production"
          ? "提示：当前系统仍处于演示模式，登录后管理员可在『管理→系统设置』正式切换。"
          : "提示：当前系统处于正式部署模式，演示账号默认不可用。";
    } else {
      $("loginError").textContent = "";
    }
  }
}

document.querySelectorAll(".login-tab").forEach((tab) => {
  tab.onclick = () => setLoginMode(tab.dataset.mode, true);
});

document.querySelectorAll(".demo-chip").forEach((chip) => {
  chip.onclick = () => {
    $("loginUser").value = chip.dataset.u;
    $("loginPass").value = chip.dataset.p;
    $("loginPass").focus();
  };
});

$("btnLogin").onclick = login;
$("loginPass").addEventListener("keydown", (e) => { if (e.key === "Enter") login(); });

async function login() {
  $("loginError").textContent = "";
  try {
    const r = await fetch("/api/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("loginUser").value.trim(), password: $("loginPass").value }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "登录失败");
    TOKEN = data.token; USER = data;
    localStorage.setItem("bid_token", TOKEN);
    localStorage.setItem("bid_user", JSON.stringify(USER));
    enterApp();
    toast("登录成功：" + USER.display_name, "success");
  } catch (e) {
    $("loginError").textContent = e.message;
    toast(e.message, "error");
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

// ============== Tabs ==============
document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
    if (tab.dataset.tab === "admin") loadAdminTab("overview");
    if (tab.dataset.tab === "tpl") loadTemplates();
  };
});

// 管理端子标签
document.querySelectorAll(".subtab").forEach((b) => {
  b.onclick = () => loadAdminTab(b.dataset.sub);
});

function loadAdminTab(name) {
  document.querySelectorAll(".subtab").forEach((b) =>
    b.classList.toggle("active", b.dataset.sub === name));
  document.querySelectorAll(".subpanel").forEach((p) =>
    p.classList.toggle("active", p.id === "sub-" + name));
  if (name === "overview") loadOverview();
  if (name === "ai") loadModelConfig();
  if (name === "tenants") loadTenants();
  if (name === "system") loadSystemSettings();
  if (name === "audit") loadAudit();
}

// ============== Markdown ==============
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

// ============== 状态/统计 ==============
async function loadStatus() {
  const h = await api("/api/health");
  const llm = h.mock_mode
    ? '<span class="badge mock">⚠ LLM:Mock</span>'
    : '<span class="badge live">● 真实模型</span>';
  const be = h.azure_search
    ? '<span class="badge live">🔎 Azure AI Search</span>'
    : '<span class="badge gray">🔎 ChromaDB</span>';
  const dep = h.deployment_mode === "production"
    ? '<span class="badge prod">🚀 正式部署</span>'
    : '<span class="badge demo">🎮 演示</span>';
  $("statusbar").innerHTML = dep + llm + be;
  await loadStats();
}

async function loadStats() {
  try {
    const s = await api("/api/stats");
    const dt = Object.entries(s.by_doc_type).map(([k, v]) => `${k}:${v}`).join("　") || "—";
    const dp = Object.entries(s.by_department).map(([k, v]) => `${k}:${v}`).join("　") || "—";
    $("kbStats").innerHTML = `
      <div class="stat-box"><div class="num">${s.total_chunks}</div><div class="lbl">知识片段总数</div></div>
      <div class="stat-box"><div class="lbl">按类型</div><div>${dt}</div></div>
      <div class="stat-box"><div class="lbl">按部门</div><div>${dp}</div></div>
      <div class="stat-box"><div class="lbl">检索后端</div><div>${s.backend}</div></div>`;
  } catch (e) { /* ignore */ }
}

// ============== 知识库 ==============
$("btnIngest").onclick = async () => {
  $("btnIngest").disabled = true;
  $("ingestLog").textContent = "正在解析文档并构建向量索引...";
  try {
    const r = await apiJson("/api/ingest", {});
    let log = `✅ 完成：处理文件 ${r.files_processed} 个，索引片段 ${r.chunks_indexed} 条（后端：${r.backend}）\n`;
    log += r.mock_mode ? "（LLM Mock 模式）\n\n" : "（真实 Embedding）\n\n";
    r.details.forEach((d) => { log += `• ${d.file} [${d.doc_type}] → ${d.chunks} 片段\n`; });
    $("ingestLog").textContent = log;
    toast(`索引完成：${r.chunks_indexed} 片段`, "success");
    await loadStats();
  } catch (e) {
    $("ingestLog").textContent = "❌ 失败：" + e.message;
    toast("索引失败：" + e.message, "error");
  }
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
    toast(`已上传 ${r.saved}`, "success");
  } catch (e) {
    $("ingestLog").textContent = "❌ " + e.message;
    toast(e.message, "error");
  }
};

// ============== 问答 ==============
$("btnAsk").onclick = async () => {
  const q = $("askInput").value.trim();
  if (!q) { toast("请输入问题", "warn"); return; }
  $("askAnswer").innerHTML = '<span class="loading">思考中...</span>';
  $("askCitations").innerHTML = "";
  try {
    const r = await apiJson("/api/ask", {
      question: q, doc_type: $("askDocType").value || null, department: $("askDept").value || null,
    });
    $("askAnswer").innerHTML = renderMarkdown(r.answer);
    renderCitations($("askCitations"), r.citations);
  } catch (e) {
    $("askAnswer").textContent = "❌ " + e.message;
    toast(e.message, "error");
  }
};

// ============== 标书生成 ==============
$("btnGen").onclick = async () => {
  const customer = $("genCustomer").value.trim();
  const req = $("genReq").value.trim();
  if (!customer || !req) { toast("请填写客户名称和 RFP 需求", "warn"); return; }
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
    toast("标书生成完成", "success");
  } catch (e) {
    $("genResult").textContent = "❌ 生成失败：" + e.message;
    toast(e.message, "error");
  }
  $("btnGen").disabled = false;
};

async function exportBid(fmt) {
  if (!LAST_BID) return;
  const r = await fetch("/api/export/" + fmt, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(LAST_BID),
  });
  if (!r.ok) { toast("导出失败", "error"); return; }
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

// ============== 概览 ==============
async function loadOverview() {
  try {
    const [h, s, c] = await Promise.all([
      api("/api/health"), api("/api/stats"), api("/api/admin/model-config"),
    ]);
    const provider = c.provider_presets.find((p) => p.id === c.provider);
    const items = [
      { label: "部署模式", value: h.deployment_mode === "production" ? "🚀 正式部署" : "🎮 演示模式" },
      { label: "AI 运行模式", value: h.mock_mode ? "⚠️ Mock" : "✅ 真实模型" },
      { label: "当前 Provider", value: (provider && provider.name) || c.provider },
      { label: "Chat 模型", value: c.chat_deployment },
      { label: "Embedding 模型", value: c.embedding_deployment },
      { label: "检索后端", value: h.backend },
      { label: "知识片段总数", value: s.total_chunks },
      { label: "API Key", value: c.api_key_set ? "已配置" : "未配置" },
    ];
    $("overviewGrid").innerHTML = items.map((it) =>
      `<div class="ov-box"><div class="ov-label">${it.label}</div><div class="ov-value">${it.value}</div></div>`).join("");
    if (h.mock_mode) {
      $("overviewTip").textContent = "⚠️ 当前为 Mock 模式（生成内容为占位）。如需真实 AI 体验，请到「AI 模型」配置 API Key 并测试连接。";
    } else {
      $("overviewTip").textContent = "✅ 系统已接入真实大模型。建议定期到「审计日志」查看操作记录。";
    }
  } catch (e) { $("overviewGrid").innerHTML = "<p class='err'>" + e.message + "</p>"; }
}

// ============== 租户/用户 ==============
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
    toast("租户已创建", "success");
  } catch (e) { toast(e.message, "error"); }
};

$("btnAddUser").onclick = async () => {
  $("adminLog").textContent = "创建中...";
  try {
    const r = await apiJson("/api/admin/users", {
      username: $("newUserName").value.trim(), password: $("newUserPass").value,
      tenant_id: $("newUserTenant").value.trim(), role: $("newUserRole").value,
    });
    $("adminLog").textContent = `✅ 已创建用户 ${r.username}（租户 ${r.tenant_id} / ${r.role}）`;
    toast(`用户 ${r.username} 已创建`, "success");
  } catch (e) {
    $("adminLog").textContent = "❌ " + e.message;
    toast(e.message, "error");
  }
};

// ============== 系统设置 ==============
async function loadSystemSettings() {
  try {
    const s = await api("/api/admin/system");
    $("sysDeployMode").value = s.deployment_mode;
    $("sysBrand").value = s.brand_name;
  } catch (e) { toast(e.message, "error"); }
}

$("btnSaveSystem").onclick = async () => {
  try {
    const r = await api("/api/admin/system", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        deployment_mode: $("sysDeployMode").value,
        brand_name: $("sysBrand").value.trim() || null,
      }),
    });
    $("appBrand").textContent = r.brand_name;
    document.title = r.brand_name;
    toast("系统设置已保存", "success");
    loadStatus();
  } catch (e) { toast(e.message, "error"); }
};

// ============== AI 模型配置 ==============
async function loadModelConfig() {
  try {
    const c = await api("/api/admin/model-config");
    $("modelMode").textContent = c.mock_mode ? "Mock 模式" : "真实模型";
    $("modelMode").className = "mode-tag " + (c.mock_mode ? "mock" : "live");
    PROVIDER_PRESETS = c.provider_presets || [];
    $("cfgProvider").innerHTML = PROVIDER_PRESETS.map((p) =>
      `<option value="${p.id}">${p.name}</option>`).join("");
    $("cfgProvider").value = c.provider;
    $("cfgBaseUrl").value = c.base_url || "";
    $("cfgAzureEndpoint").value = c.azure_endpoint || "";
    $("cfgApiVersion").value = c.api_version || "";
    $("cfgApiKey").value = "";
    $("cfgApiKey").placeholder = c.api_key_set
      ? `已配置：${c.api_key_masked}（留空不修改）`
      : "粘贴服务商 API Key";
    $("cfgMock").value = c.mock_mode_setting;
    $("cfgChat").value = c.chat_deployment;
    $("cfgEmbed").value = c.embedding_deployment;
    $("cfgTemp").value = c.temperature;
    $("chatPresets").innerHTML = c.chat_presets.map((p) => `<option value="${p}">`).join("");
    $("embedPresets").innerHTML = c.embedding_presets.map((p) => `<option value="${p}">`).join("");
    checkProviderVisibility(c.provider);
    checkMockWarn(c);
    const ov = [];
    if (c.provider_overridden) ov.push("Provider");
    if (c.api_key_overridden) ov.push("API Key");
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
      "⚠️ 当前 Provider 未配置有效 API Key / Endpoint / Base URL，强制『真实』无法生效，系统仍将使用 Mock。请在本面板填写 API Key 与服务地址。";
  } else if (sel === "on") {
    $("modelWarn").textContent = "ℹ️ 已强制 Mock 模式：生成为占位内容，不消耗调用，适合离线演示。";
  } else {
    $("modelWarn").textContent = "";
  }
}
$("cfgMock").addEventListener("change", () => checkMockWarn());

function checkProviderVisibility(providerId) {
  const p = PROVIDER_PRESETS.find((x) => x.id === providerId);
  const isAzure = p && p.mode === "azure";
  $("lblBaseUrl").style.display = isAzure ? "none" : "block";
  $("lblAzureEndpoint").style.display = isAzure ? "block" : "none";
  $("lblApiVersion").style.display = isAzure ? "block" : "none";
  if (p && p.note) $("modelWarn").textContent = p.note;
}

$("cfgProvider").addEventListener("change", () => {
  const p = PROVIDER_PRESETS.find((x) => x.id === $("cfgProvider").value);
  if (!p) return;
  if (p.base_url) $("cfgBaseUrl").value = p.base_url;
  if (p.chat) $("cfgChat").value = p.chat;
  if (p.embedding) $("cfgEmbed").value = p.embedding;
  checkProviderVisibility(p.id);
  checkMockWarn();
});

$("cfgEmbed").addEventListener("input", () => {
  const prev = $("modelWarn").textContent;
  const msg = "⚠️ 更换 Embedding 模型会改变向量维度，保存后请到『知识库』重建索引。";
  if (!prev.includes("向量维度")) $("modelWarn").textContent = (prev ? prev + " " : "") + msg;
});

$("btnSaveModel").onclick = async () => {
  $("modelLog").textContent = "保存中...";
  try {
    const body = {
      provider: $("cfgProvider").value,
      base_url: $("cfgBaseUrl").value.trim() || null,
      azure_endpoint: $("cfgAzureEndpoint").value.trim() || null,
      api_version: $("cfgApiVersion").value.trim() || null,
      api_key: $("cfgApiKey").value.trim() || null,
      mock_mode: $("cfgMock").value,
      chat_deployment: $("cfgChat").value.trim() || null,
      embedding_deployment: $("cfgEmbed").value.trim() || null,
      temperature: $("cfgTemp").value === "" ? null : parseFloat($("cfgTemp").value),
    };
    await api("/api/admin/model-config", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    toast("AI 模型配置已保存", "success");
    await loadModelConfig();
    await loadStatus();
  } catch (e) { $("modelLog").textContent = "❌ " + e.message; toast(e.message, "error"); }
};

$("btnTestModel").onclick = async () => {
  $("btnTestModel").disabled = true;
  $("modelLog").textContent = "🧪 正在测试连接...";
  try {
    const r = await api("/api/admin/model-config/test", { method: "POST" });
    const tag = r.ok ? "✅" : "❌";
    $("modelLog").textContent =
      `${tag} ${r.message}\n模式：${r.mode}　延迟：${r.latency_ms} ms\n样例输出：${r.sample || "（无）"}`;
    toast(r.ok ? `连接成功（${r.latency_ms}ms）` : "连接失败", r.ok ? "success" : "error");
  } catch (e) { $("modelLog").textContent = "❌ " + e.message; toast(e.message, "error"); }
  $("btnTestModel").disabled = false;
};

$("btnResetModel").onclick = async () => {
  if (!confirm("确认恢复为 .env 默认模型配置？")) return;
  try {
    await api("/api/admin/model-config", {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset: true }),
    });
    $("modelWarn").textContent = "";
    toast("已恢复默认", "success");
    await loadModelConfig();
  } catch (e) { toast(e.message, "error"); }
};

// ============== 审计 ==============
$("btnRefreshAudit").onclick = (e) => { e.preventDefault(); e.stopPropagation(); loadAudit(); };
$("auditScope").onclick = (e) => e.stopPropagation();
$("auditScope").onchange = (e) => { e.stopPropagation(); loadAudit(); };

async function loadAudit() {
  try {
    const rows = await api("/api/admin/audit?scope=" + $("auditScope").value);
    if (!rows.length) { $("auditTable").innerHTML = '<p class="empty">暂无记录</p>'; return; }
    $("auditTable").innerHTML =
      '<table><thead><tr><th>时间</th><th>用户</th><th>租户</th><th>操作</th><th>详情</th></tr></thead><tbody>' +
      rows.map((r) =>
        `<tr><td>${r.time}</td><td>${r.username}</td><td>${r.tenant_id}</td>` +
        `<td><span class="act">${r.action}</span></td><td class="detail">${(r.detail || "").slice(0, 120)}</td></tr>`
      ).join("") + "</tbody></table>";
  } catch (e) { $("auditTable").textContent = e.message; }
}

// ============== 章节模板（按分类折叠） ==============
async function loadTemplates() {
  try {
    const list = await api("/api/templates");
    TEMPLATES_CACHE = list;
    // 标书生成下拉（按 category 分组）
    const sel = $("genTemplate");
    const byCat = groupBy(list, (t) => t.category || "其他");
    sel.innerHTML = Object.keys(byCat).map((cat) =>
      `<optgroup label="${cat}">` +
      byCat[cat].map((t) =>
        `<option value="${t.id}">${t.name}（${t.sections.length}章${t.builtin ? "" : "·自定义"}）</option>`
      ).join("") + "</optgroup>"
    ).join("");
    // 模板管理（折叠 group）
    renderTplGroups("");
  } catch (e) { if ($("tplGroups")) $("tplGroups").textContent = e.message; }
}

function groupBy(arr, fn) {
  const out = {};
  for (const x of arr) {
    const k = fn(x);
    (out[k] = out[k] || []).push(x);
  }
  return out;
}

function renderTplGroups(keyword) {
  const kw = (keyword || "").trim().toLowerCase();
  const matched = !kw ? TEMPLATES_CACHE : TEMPLATES_CACHE.filter((t) =>
    t.name.toLowerCase().includes(kw) ||
    (t.category || "").toLowerCase().includes(kw) ||
    t.sections.join(" ").toLowerCase().includes(kw)
  );
  const byCat = groupBy(matched, (t) => t.category || "其他");
  const cats = Object.keys(byCat);
  if (!cats.length) { $("tplGroups").innerHTML = '<p class="empty">没有匹配的模板</p>'; return; }
  $("tplGroups").innerHTML = cats.map((cat, i) => `
    <details class="tpl-group" ${i === 0 || kw ? "open" : ""}>
      <summary><span>📂 ${cat}</span><span class="grp-count">${byCat[cat].length} 套</span></summary>
      <div class="tpl-cards">
        ${byCat[cat].map((t) => `
          <div class="tpl-card">
            <div class="tpl-head">
              <strong>${t.name}</strong>
              ${t.builtin
                ? '<span class="tpl-badge">内置</span>'
                : `<span class="tpl-badge custom">自定义</span> <button class="tpl-del" data-id="${t.id}">删除</button>`}
            </div>
            <ol>${t.sections.map((s) => `<li>${s}</li>`).join("")}</ol>
          </div>`).join("")}
      </div>
    </details>`).join("");
  document.querySelectorAll(".tpl-del").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("确认删除该模板？")) return;
      try {
        await api("/api/templates/" + encodeURIComponent(b.dataset.id), { method: "DELETE" });
        toast("模板已删除", "success"); loadTemplates();
      } catch (e) { toast(e.message, "error"); }
    };
  });
}

$("tplSearch").addEventListener("input", (e) => renderTplGroups(e.target.value));
$("btnExpandAll").onclick = () =>
  document.querySelectorAll("#tplGroups .tpl-group").forEach((d) => d.open = true);
$("btnCollapseAll").onclick = () =>
  document.querySelectorAll("#tplGroups .tpl-group").forEach((d) => d.open = false);

$("btnAddTpl").onclick = async () => {
  const name = $("newTplName").value.trim();
  const sections = $("newTplSections").value.split("\n").map((s) => s.trim()).filter(Boolean);
  if (!name || !sections.length) { toast("请填写名称和至少一个章节", "warn"); return; }
  try {
    await apiJson("/api/templates", { name, sections });
    toast(`已保存模板「${name}」`, "success");
    $("newTplName").value = ""; $("newTplSections").value = "";
    loadTemplates();
  } catch (e) { toast(e.message, "error"); }
};

// ============== 启动 ==============
loadPublicSystemInfo();
if (TOKEN && USER) {
  enterApp();
} else {
  $("loginOverlay").classList.remove("hidden");
}
