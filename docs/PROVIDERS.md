# Провайдеры моделей и параметры генерации

## Как выбрать провайдера

Сайдбар → **Провайдер**:

- **Ollama** — локальный [Ollama](https://ollama.ai/) (нативный API `/api/*`,
  автодетект OpenAI-режима, если нативный недоступен). URL из `DEFAULT_OLLAMA_URL`.
- **vLLM** — [vLLM](https://docs.vllm.ai/) или любой сервер с OpenAI-совместимым
  API. URL из `DEFAULT_VLLM_URL`, ключ (если нужен) — `VLLM_API_KEY`.
- **Custom API (OpenAI-compatible)** — OpenAI, OpenRouter, self-hosted endpoints.
  **Base URL и API-ключ настраиваются прямо в сайдбаре** (значения по умолчанию —
  из `DEFAULT_CUSTOM_URL` / `DEFAULT_CUSTOM_API_KEY`).

Для Custom важно: URL указывается **без** `/v1` — клиент сам добавит
`/v1/chat/completions`, `/v1/models`.

### Список моделей

По умолчанию список берётся с сервера:

| Провайдер | Эндпоинт |
|-----------|----------|
| Ollama (native) | `GET /api/tags` |
| Ollama (OpenAI-режим), vLLM, Custom | `GET /v1/models` |

Если у Custom-эндпоинта `/v1/models` недоступен — в сайдбаре появится поле
«Название модели» (вручную) и fallback-список из `DEFAULT_CUSTOM_MODELS` в `.env`.

### Контекстное окно

Приложение пытается определить размер контекстного окна модели (`/api/show` для
Ollama, поля `/v1/models` для OpenAI-совместимых) и показывает рекомендуемый
диапазон размера чанка. Если определить не удалось — подсказка просто скрывается.

## Параметры генерации

Сайдбар → «Параметры генерации». Значения пробрасываются в каждый запрос
(чат, анализ чанков, финальный отчёт):

| Параметр | UI | Ollama native (`options`) | OpenAI-compatible |
|----------|----|---------------------------|-------------------|
| temperature | слайдер 0–2 | `temperature` | `temperature` |
| top_p | слайдер 0–1 | `top_p` | `top_p` |
| max_tokens | число (0 = не передавать) | `num_predict` | `max_tokens` |

Реализация: `src/llm_client.py`, dataclass `GenerationParams`.

Пример сырых payload'ов:

```jsonc
// Ollama native
{"model": "qwen2.5:7b", "messages": [...], "stream": true,
 "options": {"temperature": 0.2, "top_p": 0.95, "num_predict": 4096}}

// OpenAI-compatible
{"model": "gpt-4o-mini", "messages": [...], "stream": true,
 "temperature": 0.2, "top_p": 0.95, "max_tokens": 4096}
```

## Свой провайдер в коде

`LLMClient` принимает `provider` (`ollama` | `vllm` | `custom`), `base_url`,
`api_key`. Любой OpenAI-совместимый сервер работает через `custom` — достаточно
`base_url` без `/v1`.
