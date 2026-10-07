# BASE_IMAGE — базовый образ с Python >= 3.11.
# По умолчанию публичный python:3.11-slim; можно передать любой другой,
# например образ из внутреннего зеркала:
#   docker compose build --build-arg BASE_IMAGE=<mirror>/python:3.12
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE} AS base
USER root

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN mkdir -p /opt/venv && python -m venv /opt/venv

# ── Зависимости ──
FROM base AS deps

# glob "poetry.lock*" совпадает и с 0 файлов — публичная сборка без него работает
COPY pyproject.toml ./
COPY poetry.lock* ./
COPY requirements.txt /app/requirements.txt

# Если есть poetry.lock (внутренняя сборка) — ставим из него,
# иначе — из requirements.txt (публичная сборка без lock-файла).
RUN set -eux; \
    if [ -f /app/poetry.lock ]; then \
        pip install --no-cache-dir "poetry==1.8.*"; \
        poetry config --local warnings.export false; \
        poetry export -f requirements.txt --output /tmp/requirements.lock.txt --without-hashes; \
        pip install --no-cache-dir -r /tmp/requirements.lock.txt; \
    else \
        pip install --no-cache-dir -r /app/requirements.txt; \
    fi

# ── Приложение ──
FROM base AS app

COPY --from=deps /opt/venv /opt/venv
COPY src /app/src
COPY src/.streamlit /app/.streamlit

# Не-рутовый пользователь (если в базовом образе app уже есть — используем его)
RUN id app >/dev/null 2>&1 || useradd --create-home --shell /bin/bash app; \
    chown -R app:app /app
USER app

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
