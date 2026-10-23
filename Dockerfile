# Suspension Check API + web page. Stateless: no volume, no database, no
# storage credentials. The container filesystem can be mounted read-only.
FROM python:3.12-slim

RUN pip install --no-cache-dir "uv>=0.8,<0.9"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /srv
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY app ./app
RUN uv sync --frozen --no-dev --extra api --extra pattern \
    && rm -rf /root/.cache

RUN useradd --system --uid 10001 --no-create-home app
USER app

ENV PORT=8000 SUSPENSION_CHECK_TRUST_PROXY=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')"
CMD ["sh", "-c", "exec uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
