<#
  一键启动脚本（Windows PowerShell）
  - 创建/复用 .venv（Python 3.11）
  - 安装依赖
  - 复制 .env（如不存在）
  - 生成示例数据（如知识库为空）
  - 启动服务
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "创建虚拟环境 (Python 3.11)..." -ForegroundColor Cyan
    py -3.11 -m venv .venv
}

$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements.txt --quiet

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "已从 .env.example 创建 .env（默认 Mock 模式）" -ForegroundColor Yellow
}

if (-not (Test-Path "data\knowledge\demo")) {
    & $py scripts\seed_data.py
}

Write-Host "启动服务： http://localhost:8000" -ForegroundColor Green
& $py -m uvicorn app.main:app --port 8000
