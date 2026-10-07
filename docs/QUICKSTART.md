# Быстрый старт

## Предварительные требования

- Docker и Docker Compose (или Python 3.11+)
- LLM-сервер: Ollama, vLLM или любой OpenAI-compatible API
- Опционально: HTTP-сервис транскрибации (вкладки «Звонки» и «Транскрибация»)

## Шаг 1: LLM-сервер

### Вариант A: Ollama (рекомендуется)

```bash
# Установка: https://ollama.ai/
ollama run qwen2.5:7b
# или: ollama run llama3.2
```

### Вариант B: vLLM

```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --port 8000
```

### Вариант C: внешний OpenAI-compatible API

Ничего запускать не нужно — подойдёт OpenAI, OpenRouter или любой self-hosted
сервер с `/v1/chat/completions`. Настройка — на шаге 2 или прямо в UI.

## Шаг 2: Конфигурация

```bash
cp .env.example .env
nano .env   # при необходимости
```

По умолчанию всё настроено для локального запуска (сервисы на хост-машине через
`host.docker.internal`). Если нужны другие адреса/ключи — правьте `.env`
(полное описание переменных — в README) или меняйте URL/ключ в сайдбаре для
Custom-провайдера.

## Шаг 3: Запуск

### Docker Compose (рекомендуется)

```bash
docker compose up --build          # или docker compose up -d --build
```

### Без Docker (для разработки)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
```

## Шаг 4: Открыть в браузере

```
http://localhost:8501
```

В сайдбаре: провайдер → модель → (опционально) параметры генерации и системный промпт.

## Типовые сценарии

### Анализ PDF-отчёта

1. Вкладка «Документы» → загрузите PDF (лимит 500 МБ)
2. Задача: «Составь executive summary с ключевыми метриками и рекомендациями»
3. Размер чанка — по рекомендации под полем (подсказка строится от контекстного окна модели)
4. «Начать» → дождаться → скачать .docx или .md

### Пакет транскриптов звонков

1. Файл с транскриптами, диалоги разделены строками `=====` / `-----` / `_____`
2. Вкладка «Документы» → режим «Всплеск обращений»
3. Задача: «Сгруппируй причины обращений и выяви основные проблемы»

### Обработка аудиозвонков

1. Вкладка «Звонки» → WAV-файлы (нужен запущенный ASR-сервис)
2. Транскрибация → анализ → отчёт

### Только транскрибация в Word

Вкладка «Транскрибация» → WAV-файлы → единый .docx со всеми диалогами.

## За прокси и внутренним зеркалом пакетов

Если docker и pip ходят через прокси с собственным TLS:

```bash
# .env
BASE_IMAGE=internal-mirror/python:3.12        # образ из внутреннего registry
REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt  # CA этого TLS
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt       # то же для ssl-модуля
HOST_PORT=8502                                       # если 8501 занят
```

- В `Dockerfile` index пакетов можно переключить на внутренний mirror
  (`PIP_INDEX_URL=...` как build-arg) — см. `pyproject.toml`/`pip.conf`.
- На старых docker-compose (v1) команды `docker-compose ...` вместо `docker compose ...`.
- Если самоподписанный сертификат у LLM/ASR-сервиса, без `REQUESTS_CA_BUNDLE`
  получите `SSLCertVerificationError` — самый частый случай.

## Остановка

```bash
docker compose down        # остановить
docker compose down -v     # остановить и очистить volumes
```

## Решение проблем

### «Connection refused» / модели не загружаются

```bash
curl http://localhost:11434/api/tags    # Ollama
curl http://localhost:8000/v1/models    # vLLM / custom
```

- Сервер запущен? Модель загружена (`ollama list`)?
- Из контейнера хост-машина доступна как `host.docker.internal`
  (в `docker-compose.yml` уже прописан `extra_hosts` для Linux).

### Custom-провайдер: «Models not loaded»

Некоторые API не отдают `/v1/models` — в этом случае в сайдбаре появится поле
«Название модели», введите вручную. Список fallback-моделей можно задать
в `.env` (`DEFAULT_CUSTOM_MODELS=model1,model2`).

### Не удалось извлечь текст

- Поддерживаются: PDF, DOCX, XLSX, TXT. Старые `.doc` конвертируйте в DOCX.
- Файл не должен быть защищён паролем.

### Медленная работа

- Меньшая модель (llama3.2:1b вместо 70b)
- Крупнее чанк (меньше запросов), но следите за подсказкой о контекстном окне
- `OLLAMA_NUM_PARALLEL=2` на стороне Ollama

### Транскрибация недоступна

Вкладки «Звонки»/«Транскрибация» требуют внешний ASR-сервис (`TRANSCRIBE_URL`
в `.env`). Готовые текстовые транскрипты можно анализировать во вкладке «Документы».

## Полезные команды

```bash
docker compose logs -f      # логи
docker compose restart      # перезапуск
docker compose ps           # статус
pytest                      # тесты (в venv с pytest)
ruff check src tests        # линтер
```

## Дополнительно

- [README](../README.md) — архитектура и конфигурация
- [docs/PROVIDERS.md](PROVIDERS.md) — провайдеры и параметры генерации
