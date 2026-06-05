#!/usr/bin/env bash
# 一键启动脚本（Linux/macOS）
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "创建虚拟环境 (Python 3.11)..."
  python3.11 -m venv .venv || python3 -m venv .venv
fi

PY=".venv/bin/python"
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已从 .env.example 创建 .env（默认 Mock 模式）"
fi

if [ ! -d "data/knowledge/demo" ]; then
  "$PY" scripts/seed_data.py
fi

echo "启动服务： http://localhost:8000"
exec "$PY" -m uvicorn app.main:app --port 8000
