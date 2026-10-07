"""Вспомогательные функции без зависимости от streamlit (тестируются юнит-тестами)."""
from __future__ import annotations

import re

import requests

__all__ = ["detect_thinking_block", "friendly_llm_error", "format_int"]


def detect_thinking_block(text: str) -> tuple[str, str]:
    """
    Выделяет блок «рассуждений» модели из ответа.
    Паттерны: <think>...</think>, **Рассуждение:**...
    Возвращает (thinking_text, answer_text).
    """
    m = re.search(r"<think>(.*?)</think>", text, re.DOTALL | re.IGNORECASE)
    if m:
        thinking = m.group(1).strip()
        answer = (text[: m.start()] + text[m.end() :]).strip()
        return thinking, answer

    m = re.match(
        r"\s*\*{0,2}(?:Рассуждени[ея]|Thinking|Reasoning|Мысли)\*{0,2}\s*:?\s*"
        r"(.*?)(?:\n\n---|\n\n\*{0,2}(?:Ответ|Answer|Результат)\*{0,2})",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        thinking = m.group(1).strip()
        answer = text[m.end() :].strip()
        if answer:
            return thinking, answer

    return "", text


def friendly_llm_error(exc: Exception) -> str:
    """
    Превращает низкоуровневое исключение requests в понятное сообщение
    с подсказкой, что проверить. Технический текст сохраняется в конце.
    """
    hint: str | None = None

    if isinstance(exc, requests.exceptions.SSLError):
        hint = (
            "Ошибка TLS: сервер использует сертификат, которому не доверяет система. "
            "Для внутренних сервисов задайте REQUESTS_CA_BUNDLE (см. .env.example)."
        )
    elif isinstance(exc, requests.exceptions.ConnectTimeout):
        hint = "Сервер не отвечает на установку соединения. Проверьте URL и запущен ли сервис."
    elif isinstance(exc, requests.exceptions.ReadTimeout):
        hint = "Сервер не успел ответить за отведённое время. Увеличьте LLM_TIMEOUT_SEC или уменьшите задачу."
    elif isinstance(exc, requests.exceptions.ConnectionError):
        hint = "Не удалось подключиться к серверу. Проверьте URL провайдера и доступность сервиса."
    elif isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 403):
            hint = "Доступ запрещён. Проверьте API-ключ и дополнительные заголовки провайдера."
        elif status == 404:
            hint = "Модель или эндпоинт не найдены (404). Проверьте название модели и базовый URL."
        elif status == 429:
            hint = "Слишком много запросов (429). Подождите немного и повторите."
        elif status is not None and status >= 500:
            hint = "Ошибка на стороне сервера модели. Попробуйте позже."
    elif isinstance(exc, ValueError):
        hint = "Некорректные входные данные."

    base = str(exc)
    if hint is None:
        return base
    return f"{hint}\n\n_Технические детали: {base[:500]}_"


def format_int(n: int) -> str:
    """1234567 -> '1 234 567' (без locale-зависимостей)."""
    return f"{n:,}".replace(",", " ")
