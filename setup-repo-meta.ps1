<#
  一键设置 GitHub 仓库的简介(About) 与 主题标签(Topics)
  依赖：GitHub CLI (https://cli.github.com/)  ——  需先执行  gh auth login

  用法：
    .\setup-repo-meta.ps1
    .\setup-repo-meta.ps1 -Repo "zm289098404-netizen/AI-"
#>
param(
    [string]$Repo = "zm289098404-netizen/AI-"
)

$ErrorActionPreference = "Stop"

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m)   { Write-Host $m -ForegroundColor Green }
function Err($m)  { Write-Host $m -ForegroundColor Red }

# ---- 0. 检查 gh 是否安装 ----
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    Err "未检测到 GitHub CLI (gh)。请先安装： https://cli.github.com/"
    Err "安装后运行： gh auth login  完成登录授权。"
    exit 1
}

# ---- 1. 检查登录状态 ----
Info "检查 gh 登录状态..."
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Err "尚未登录 GitHub。请先运行： gh auth login"
    exit 1
}

# ---- 2. 设置简介 ----
$description = "RAG 智能投标/方案生成助手 · FastAPI + Azure OpenAI + ChromaDB · 多租户 · Word/PDF 导出"

Info "`n设置仓库简介..."
gh repo edit $Repo --description $description
Ok "  简介已设置。"

# ---- 3. 设置主题标签 ----
$topics = @(
    "rag", "llm", "azure-openai", "fastapi", "chromadb",
    "retrieval-augmented-generation", "python", "vector-search",
    "semantic-search", "presales", "proposal-generator", "multi-tenant",
    "bidding", "knowledge-base", "ai-assistant", "document-generation", "chinese-nlp"
)

Info "`n设置主题标签 ($($topics.Count) 个)..."
$topicArgs = @()
foreach ($t in $topics) { $topicArgs += "--add-topic"; $topicArgs += $t }
gh repo edit $Repo @topicArgs
Ok "  标签已设置。"

Ok "`n[完成] 已更新仓库元数据： https://github.com/$Repo"
Info "可刷新仓库主页右侧 About 区域查看效果。"
