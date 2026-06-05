# 智能投标 / 方案生成系统 — 容器镜像
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖以利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY app ./app
COPY web ./web
COPY scripts ./scripts

# 数据目录（知识库 / 向量库 / SQLite）建议挂载卷持久化
RUN mkdir -p data/knowledge data/chroma

EXPOSE 8000

# 容器启动：若知识库为空则生成示例数据，然后启动服务
CMD ["sh", "-c", "[ -z \"$(ls -A data/knowledge 2>/dev/null)\" ] && python scripts/seed_data.py; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
