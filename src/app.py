"""
SimAssistant — чат с LLM, анализ документов и обработка звонков.
Провайдеры: Ollama, vLLM, любой OpenAI-compatible API.
"""
from __future__ import annotations

import contextlib
import html
import inspect
import time
from datetime import datetime
from typing import Any

import streamlit as st

from analyzer import AnalysisCancelled, run_chunked_analysis
from chunking import ChunkingSettings
from config import settings
from document_extractors import extract_text
from exceptions import CancelledError
from exporters import chat_to_pdf, markdown_to_docx, transcriptions_to_docx
from llm_client import GenerationParams, LLMClient
from styles import CUSTOM_CSS, DARK_CSS
from transcribe_client import TranscribeClient
from utils import detect_thinking_block, format_int, friendly_llm_error

# st.chat_input с файлами появился в streamlit 1.44
_CHAT_FILES_SUPPORTED = "accept_file" in inspect.signature(st.chat_input).parameters
# Прокручиваемый контейнер фиксированной высоты и width="stretch" — новые API
_CONTAINER_HEIGHT_SUPPORTED = "height" in inspect.signature(st.container).parameters
_BUTTON_WIDTH_KW = (
    {"width": "stretch"}
    if "width" in inspect.signature(st.button).parameters
    else {"use_container_width": True}
)
_CHAT_HISTORY_PX = 560

# ──────────────────────────────────────────────
# Параметры анализа по умолчанию (можно менять в UI)
# ──────────────────────────────────────────────
DOC_CHUNK_SIZE = 12_000
DOC_CHUNK_OVERLAP = 400
DOC_SPLIT_STRATEGY = "smart"
DOC_CUSTOM_SEPARATOR = r"_{3,}|-{3,}|={3,}"

CALLS_CHUNK_SIZE = 12_000
CALLS_CHUNK_OVERLAP = 400
CALLS_SPLIT_STRATEGY = "paragraphs"
CALLS_CUSTOM_SEPARATOR = r"_{3,}|-{3,}|={3,}"

DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.95

# ──────────────────────────────────────────────
# Провайдеры LLM
# ──────────────────────────────────────────────
PROVIDER_LABELS = {
    "ollama": "Ollama",
    "vllm": "vLLM",
    "custom": "Custom API (OpenAI-compatible)",
}
PROVIDER_BY_LABEL = {label: key for key, label in PROVIDER_LABELS.items()}

# ──────────────────────────────────────────────
# Шаблоны задач анализа
# ──────────────────────────────────────────────
NO_PRESET = "— без шаблона —"

DOC_PRESETS = {
    NO_PRESET: "",
    "Краткое резюме (exec summary)": (
        "Составь краткое резюме документов: цель, ключевые тезисы, важные цифры и выводы. До 300 слов."
    ),
    "Риски и обязательства": (
        "Найди все риски, обязательства, сроки и условия.\nДля каждого — цитату и место в документе."
    ),
    "Ключевые цифры и метрики": (
        "Вытащи все числовые метрики и факты в таблицу: значение, контекст, раздел/страница источника."
    ),
}

CALLS_PRESETS = {
    NO_PRESET: "",
    "Причины обращений": (
        "Определи основные причины обращений клиентов, сгруппируй их и оцени относительную частоту каждой группы."
    ),
    "Referral-анализ": (
        "Найди все случаи перенаправления между компаниями/подразделениями:\n"
        "кто кого направил и какими словами это сказано."
    ),
    "Недовольство и эскалации": (
        "Отметь проявления недовольства клиентов, угрозы жалоб и эскалации — с цитатами и dialogue_id."
    ),
}


def _apply_task_preset(presets: dict[str, str], preset_key: str, goal_key: str) -> None:
    selected = st.session_state.get(preset_key, NO_PRESET)
    if selected and selected != NO_PRESET:
        st.session_state[goal_key] = presets[selected]


_PROBE_TTL_SEC = 30


def _probe_provider(provider: str, base_url: str, api_key: str) -> tuple[bool, str, int]:
    """
    Проверка доступности провайдера. Ручной кэш на 30 с в session_state:
    возвращает (ок, описание, сколько секунд назад проверяли).
    """
    now = time.time()
    cache = st.session_state.get("_probe_cache")
    sig = (provider, base_url, api_key)
    if cache and cache["sig"] == sig and now - cache["ts"] < _PROBE_TTL_SEC:
        return cache["ok"], cache["info"], int(now - cache["ts"])
    try:
        llm = LLMClient(
            provider=provider,
            base_url=base_url,
            timeout_sec=6,
            api_key=api_key or None,
            extra_headers=settings.extra_headers_for(provider),
        )
        models = llm.list_models()
        ok, info = True, f"на связи, моделей: {len(models.models)}"
    except Exception as e:
        ok, info = False, str(e)[:140]
    st.session_state["_probe_cache"] = {"sig": sig, "ts": now, "ok": ok, "info": info}
    return ok, info, 0


def _default_base_url(provider: str) -> str:
    if provider == "ollama":
        return settings.DEFAULT_OLLAMA_URL
    if provider == "vllm":
        return settings.DEFAULT_VLLM_URL
    return settings.DEFAULT_CUSTOM_URL


# ──────────────────────────────────────────────
# Streamlit page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="SimAssistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)

def _current_theme() -> str:
    return st.session_state.get("ui_theme", "dark")


st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
if _current_theme() == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
def _init_session_state() -> None:
    st.session_state.setdefault("cancel", False)
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("doc_attached_files", [])
    st.session_state.setdefault("model_list", [])
    st.session_state.setdefault("ollama_api_type", None)
    st.session_state.setdefault("llm_provider", "ollama")
    st.session_state.setdefault("llm_base_url", settings.DEFAULT_OLLAMA_URL)
    st.session_state.setdefault("llm_model", "")
    st.session_state.setdefault("custom_api_key", settings.DEFAULT_CUSTOM_API_KEY or "")
    st.session_state.setdefault("system_prompt", "")
    st.session_state.setdefault("temperature", DEFAULT_TEMPERATURE)
    st.session_state.setdefault("top_p", DEFAULT_TOP_P)
    st.session_state.setdefault("max_tokens", 0)
    st.session_state.setdefault("doc_chunk_size", DOC_CHUNK_SIZE)
    st.session_state.setdefault("calls_chunk_size", CALLS_CHUNK_SIZE)
    st.session_state.setdefault("model_context_window_cache", {})
    st.session_state.setdefault("models_loaded", False)
    # Сохранённые результаты (переживают любой rerun)
    st.session_state.setdefault("doc_report", None)
    st.session_state.setdefault("calls_report", None)
    st.session_state.setdefault("export_docx", None)
    # Непрерванный (остановленный) хвост генерации чата
    st.session_state.setdefault("chat_partial", "")


_init_session_state()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _cancel_check() -> bool:
    return bool(st.session_state.get("cancel", False))


def _reset_cancel() -> None:
    st.session_state["cancel"] = False


def _set_cancel() -> None:
    st.session_state["cancel"] = True


def _current_generation() -> GenerationParams:
    return GenerationParams(
        temperature=float(st.session_state.get("temperature", DEFAULT_TEMPERATURE)),
        top_p=float(st.session_state.get("top_p", DEFAULT_TOP_P)),
        max_tokens=int(st.session_state.get("max_tokens", 0) or 0) or None,
    )


@st.cache_data(show_spinner="Извлекаю текст из файла...")
def _extract_text_cached(file_name: str, file_bytes: bytes) -> str:
    return extract_text(file_name, file_bytes)


def _extract_files_text(uploaded_files: list[Any]) -> list[dict]:
    extracted: list[dict] = []
    for f in uploaded_files:
        if f is None:
            continue
        file_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()
        file_name = getattr(f, "name", "file")
        try:
            text = _extract_text_cached(file_name, file_bytes)
            if not text.strip():
                st.warning(f"Файл «{file_name}» пуст или не удалось извлечь текст.")
                continue
            extracted.append({"name": file_name, "text": text})
        except Exception as e:
            st.warning(f"Ошибка извлечения «{file_name}»: {e}")
    return extracted


def _build_docs_block(docs: list[dict]) -> str:
    return "\n\n".join(f"--- Документ: {d['name']} ---\n{d['text']}" for d in docs)


def _build_chat_user_prompt(message: str, attached_docs: list[dict]) -> str:
    if not attached_docs:
        return message
    return message + "\n\n" + _build_docs_block(attached_docs)


def _context_cache_key() -> str:
    provider = st.session_state.get("llm_provider", "")
    base_url = st.session_state.get("llm_base_url", "")
    model = st.session_state.get("llm_model", "")
    return f"{provider}|{base_url}|{model}"


def _get_current_model_context_window() -> int | None:
    model = (st.session_state.get("llm_model") or "").strip()
    if not model:
        return None

    cache = st.session_state.get("model_context_window_cache", {}) or {}
    key = _context_cache_key()
    if key in cache:
        return cache.get(key)

    try:
        llm = build_llm()
        value = llm.get_model_context_window(model)
    except Exception:
        value = None

    cache[key] = value
    st.session_state["model_context_window_cache"] = cache
    return value


def _recommended_chunk_range(context_window_tokens: int) -> tuple[int, int]:
    """
    Возвращает рекомендованный диапазон размера чанка в символах.
    """
    chars_per_token = 3.5
    min_chars = int(context_window_tokens * 0.35 * chars_per_token)
    max_chars = int(context_window_tokens * 0.55 * chars_per_token)
    return max(1000, min_chars), max(1500, max_chars)


def _render_chunk_guidance(*, selected_chunk_size: int) -> None:
    ctx = _get_current_model_context_window()
    if not ctx:
        st.caption("Рекомендуемый диапазон: нет данных о контекстном окне текущей модели.")
        return

    rec_min, rec_max = _recommended_chunk_range(ctx)
    hard_risk = int(ctx * 0.70 * 3.5)  # высокий риск переполнения окна на шагах с накоплением summary

    st.caption(
        f"Контекст модели: ~{ctx} токенов. "
        f"Рекомендуемый размер чанка: {format_int(rec_min)}–{format_int(rec_max)} символов."
    )

    if selected_chunk_size > hard_risk:
        st.warning(f"Размер {format_int(selected_chunk_size)} рискован: высокий риск переполнения контекстного окна.")
    elif selected_chunk_size > rec_max:
        st.info(f"Размер {format_int(selected_chunk_size)} выше рекомендуемого — возможна меньшая стабильность.")
    elif selected_chunk_size < rec_min:
        st.info(f"Размер {format_int(selected_chunk_size)} ниже рекомендуемого — анализ может быть менее целостным.")


# ──────────────────────────────────────────────
# LLM helpers
# ──────────────────────────────────────────────
def build_llm() -> LLMClient:
    provider = st.session_state["llm_provider"]
    api_key: str | None = None
    if provider == "vllm":
        api_key = settings.VLLM_API_KEY
    elif provider == "custom":
        api_key = st.session_state.get("custom_api_key") or settings.DEFAULT_CUSTOM_API_KEY
    return LLMClient(
        provider=provider,
        base_url=st.session_state["llm_base_url"],
        timeout_sec=int(st.session_state.get("llm_timeout_sec", settings.LLM_TIMEOUT_SEC)),
        ollama_api_type=st.session_state.get("ollama_api_type"),
        api_key=api_key,
        extra_headers=settings.extra_headers_for(provider),
    )


def refresh_models() -> None:
    provider = st.session_state["llm_provider"]
    llm = build_llm()
    try:
        models_info = llm.list_models()
        models, api_type = models_info.models, models_info.api_type
    except Exception:
        # У custom-API список моделей может быть недоступен — фолбэк на список из .env
        if provider == "custom":
            models, api_type = settings.custom_models, None
        else:
            raise

    st.session_state["model_list"] = models
    st.session_state["ollama_api_type"] = api_type
    st.session_state["models_loaded"] = True
    st.session_state["model_context_window_cache"] = {}
    if models and (not st.session_state.get("llm_model") or st.session_state["llm_model"] not in models):
        st.session_state["llm_model"] = models[0]


# ──────────────────────────────────────────────
# Sidebar — провайдер, модель, параметры генерации
# ──────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        # Переключатель темы: иконка луны/солнца, как в привычных сервисах
        is_dark = _current_theme() == "dark"
        head = st.columns([5, 1])
        with head[0]:
            st.markdown("## Настройки")
        with head[1]:
            st.markdown('<div class="theme-slot"></div>', unsafe_allow_html=True)
            if st.button(
                "",
                icon="☀️" if is_dark else "🌙",
                key="theme_toggle",
                help="Светлая тема" if is_dark else "Тёмная тема",
            ):
                st.session_state["ui_theme"] = "light" if is_dark else "dark"
                st.rerun()

        labels = list(PROVIDER_LABELS.values())
        current_provider = st.session_state.get("llm_provider", "ollama")
        current_label = PROVIDER_LABELS.get(current_provider, labels[0])

        selected_label = st.selectbox(
            "Провайдер",
            labels,
            index=labels.index(current_label),
            key="sidebar_provider_select",
        )
        new_provider = PROVIDER_BY_LABEL[selected_label]

        if new_provider != current_provider:
            st.session_state["llm_provider"] = new_provider
            st.session_state["llm_base_url"] = _default_base_url(new_provider)
            st.session_state["models_loaded"] = False
            st.session_state["model_list"] = []
            st.session_state["llm_model"] = ""
            st.session_state["ollama_api_type"] = None
            st.session_state["model_context_window_cache"] = {}
            try:
                refresh_models()
            except Exception as e:
                st.sidebar.warning(f"Модели не загрузились: {friendly_llm_error(e)}")

        provider = st.session_state["llm_provider"]

        # Выбор модели
        model_list = st.session_state.get("model_list", []) or []
        if provider == "custom" and not model_list:
            default_model = settings.custom_models[0] if settings.custom_models else ""
            st.session_state["llm_model"] = st.text_input(
                "Название модели",
                value=st.session_state.get("llm_model") or default_model,
                placeholder="Например: gpt-4o-mini или Qwen/Qwen2.5-7B-Instruct",
                help="Список не удалось получить с /v1/models — укажите модель вручную",
            )
        elif model_list:
            current = st.session_state.get("llm_model", "")
            idx = model_list.index(current) if current in model_list else 0
            st.session_state["llm_model"] = st.selectbox(
                "Модель",
                model_list,
                index=idx,
                key="sidebar_model",
            )
        else:
            st.info("Модели не загружены. Нажмите «Обновить».")

        if st.button("Обновить список моделей", key="sidebar_refresh"):
            try:
                st.session_state.pop("_probe_cache", None)
                refresh_models()
                st.rerun()
            except Exception as e:
                st.error(f"Не удалось обновить список моделей: {friendly_llm_error(e)}")

        # Статус подключения к провайдеру (кэш 30 с)
        if provider == "vllm":
            probe_key = settings.VLLM_API_KEY or ""
        elif provider == "custom":
            probe_key = st.session_state.get("custom_api_key") or settings.DEFAULT_CUSTOM_API_KEY or ""
        else:
            probe_key = ""
        ok, info, age = _probe_provider(provider, st.session_state["llm_base_url"], probe_key)
        if age:
            info = f"{info} · обновлено {age} с назад"
        _render_connection_status(ok, info)

        # Редко редактируемое — по свёрнутым экспандерам (≤6 строк на экране)
        if provider == "custom":
            with st.expander("API-подключение", expanded=False):
                st.session_state.setdefault("sidebar_custom_url", settings.DEFAULT_CUSTOM_URL)
                base_url = st.text_input(
                    "API Base URL",
                    key="sidebar_custom_url",
                    help="Базовый URL без /v1, например https://api.openai.com или http://my-server:8000",
                )
                st.session_state["llm_base_url"] = base_url.strip() or settings.DEFAULT_CUSTOM_URL
                api_key = st.text_input(
                    "API ключ",
                    key="sidebar_custom_api_key_input",
                    value=st.session_state.get("custom_api_key", ""),
                    type="password",
                )
                st.session_state["custom_api_key"] = api_key.strip()

        with st.expander("Параметры генерации", expanded=False):
            st.session_state["temperature"] = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(st.session_state.get("temperature", DEFAULT_TEMPERATURE)),
                step=0.05,
                help="Ниже — детерминированнее, выше — креативнее",
            )
            st.session_state["top_p"] = st.slider(
                "Top-p (nucleus sampling)",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.get("top_p", DEFAULT_TOP_P)),
                step=0.05,
            )
            st.session_state["max_tokens"] = st.number_input(
                "Max tokens (0 — по умолчанию сервера)",
                min_value=0,
                max_value=131_072,
                value=int(st.session_state.get("max_tokens", 0)),
                step=256,
            )

        with st.expander("Системный промпт", expanded=False):
            st.session_state["system_prompt"] = st.text_area(
                "Системный промпт",
                value=st.session_state.get("system_prompt", "") or "",
                height=120,
                key="sidebar_system_prompt",
                placeholder="Введите системный промпт (необязательно)...",
                label_visibility="collapsed",
            )

        st.caption("Подключение по умолчанию настраивается через .env (см. .env.example).")


# ──────────────────────────────────────────────
# Автозагрузка моделей при первом запуске
# ──────────────────────────────────────────────
def _auto_load_models() -> None:
    if not st.session_state.get("models_loaded"):
        with contextlib.suppress(Exception):
            refresh_models()


# ──────────────────────────────────────────────
# Индикатор статуса подключения
# ──────────────────────────────────────────────
def _render_connection_status(ok: bool, text: str) -> None:
    st.markdown(
        f'<span class="st-dot {"ok" if ok else "bad"}"></span>'
        f'<span class="st-dot-text">{html.escape(text)}</span>',
        unsafe_allow_html=True,
    )


def _eta_hint(elapsed_sec: int, idx: int, total: int) -> str:
    """Грубая экстраполяция: средняя длительность чанка × осталось чанков."""
    if idx < 2 or idx >= total:
        return ""
    per_chunk = elapsed_sec / (idx - 1)
    return f" · осталось ~{int(per_chunk * (total - idx))} с"


# ──────────────────────────────────────────────
# Рендер сохранённого отчёта (переживает rerun)
# ──────────────────────────────────────────────
def _render_report(*, report: dict, file_stem: str) -> None:
    with st.container(border=True):
        col_docx, col_md, col_cp, *_ = st.columns([1, 1, 1, 4])
        with col_docx:
            try:
                docx_file = markdown_to_docx(report["markdown"])
                st.download_button(
                    label="Скачать .docx",
                    data=docx_file,
                    file_name=f"{file_stem}_{report['timestamp']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_{file_stem}_docx",
                )
            except Exception as e:
                st.warning(f"Не удалось создать Word файл: {e}")
        with col_md:
            st.download_button(
                label="Скачать .md",
                data=report["markdown"].encode("utf-8"),
                file_name=f"{file_stem}_{report['timestamp']}.md",
                mime="text/markdown",
                key=f"download_{file_stem}_md",
            )
        with col_cp, st.popover("", icon="📋", key=f"copy_md_{file_stem}", help="Скопировать markdown"):
            st.code(report["markdown"], language="markdown")
        st.markdown(report["markdown"])
        with st.expander("Детали: план и заметки по частям", expanded=False):
            st.markdown("**План анализа:**")
            st.code(report["plan"], language="text")
            for idx, notes in report["notes"]:
                st.markdown(f"**Часть {idx}**")
                st.code(notes, language="text")


def _save_report(key: str, result: Any) -> None:
    st.session_state[key] = {
        "markdown": result.final_markdown,
        "plan": result.plan,
        "notes": [(n.idx, n.notes) for n in result.per_chunk_notes],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }


# ──────────────────────────────────────────────
# ТАБ 1: Чат (стиль ChatGPT)
# ──────────────────────────────────────────────
def _append_assistant(text: str, started_monotonic: float, *, stopped: bool = False) -> None:
    st.session_state["chat_messages"].append(
        {
            "role": "assistant",
            "content": text + ("\n\n_(генерация прервана)_" if stopped else ""),
            "meta": {
                "model": st.session_state.get("llm_model", ""),
                "sec": round(time.monotonic() - started_monotonic, 1),
                "tokens": max(1, round(len(text) / 3.5)),
            },
        }
    )


def _stream_assistant() -> bool:
    """
    Стримит ответ ассистента по текущей истории (последним должен быть user).
    Возвращает True, если ответ добавлен полностью.
    """
    st.session_state["cancel"] = False
    st.session_state["chat_partial"] = ""

    llm = build_llm()
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state["chat_messages"]
        if m["role"] in ("user", "assistant")
    ]
    started = time.monotonic()
    assistant_text = ""

    try:
        stream_gen = llm.chat_completion(
            model=st.session_state["llm_model"],
            system_prompt=st.session_state.get("system_prompt", "") or None,
            user_prompt="",  # не используется, когда передан messages
            generation=_current_generation(),
            stream=True,
            cancel_check=_cancel_check,
            messages=api_messages,
        )

        with st.chat_message("assistant"):
            placeholder = st.empty()
            for token in stream_gen:  # type: ignore[union-attr]
                assistant_text += token
                # держим в session_state, чтобы текст не потерялся при прерывании скрипта
                st.session_state["chat_partial"] = assistant_text
                placeholder.markdown(assistant_text + "▌")
                if _cancel_check():
                    break
            placeholder.markdown(assistant_text)

        st.session_state["chat_partial"] = ""
        _append_assistant(assistant_text, started)
        return True

    except CancelledError:
        st.session_state["chat_partial"] = ""
        if assistant_text:
            _append_assistant(assistant_text, started, stopped=True)
        st.info("Генерация остановлена")
    except Exception as e:
        st.session_state["chat_partial"] = ""
        st.error(f"Ошибка генерации: {friendly_llm_error(e)}")
    return False


def _chat_export_pdf() -> bytes:
    return chat_to_pdf(st.session_state["chat_messages"])


_CHAT_FILE_TYPES = ["pdf", "docx", "xlsx", "txt"]


def _append_user_message(text: str, files: list[Any] | None = None) -> None:
    docs = _extract_files_text(files) if files else []
    full_prompt = _build_chat_user_prompt(text, docs)
    display = text + (f"\n\nФайлы: {', '.join(d['name'] for d in docs)}" if docs else "")
    st.session_state["chat_messages"].append({"role": "user", "content": full_prompt, "display": display})
    st.session_state["chat_need_response"] = True


def _mark_regen() -> None:
    msgs = st.session_state["chat_messages"]
    if msgs and msgs[-1]["role"] == "assistant":
        msgs.pop()
    if msgs:
        st.session_state["chat_need_response"] = True


def _chat_input_widget() -> tuple[bool, str, list[Any]]:
    """Поле ввода: текст + файлы одним действием (вложения — streamlit >= 1.44)."""
    if _CHAT_FILES_SUPPORTED:
        raw = st.chat_input(
            "Напишите сообщение или приложите документ…",
            accept_file="multiple",
            file_type=_CHAT_FILE_TYPES,
        )
        if raw is None:
            return False, "", []
        return True, (raw.text or "").strip(), list(raw.files or [])
    text_only = st.chat_input("Напишите сообщение…")
    return bool(text_only), (text_only or "").strip(), []


@st.fragment
def run_chat() -> None:
    # Верхняя панель: только иконки, справа
    _has_chat = bool(st.session_state["chat_messages"])
    bar = st.columns([10, 1, 1])
    with bar[1]:
        if _has_chat:
            st.download_button(
                label="",
                icon="📄",
                data=_chat_export_pdf(),
                file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key="chat_export",
                help="Скачать историю чата в PDF",
            )
    with bar[2], st.popover("", icon="🗑", key="chat_clear_pop", help="Очистить историю"):
        st.markdown("Очистить всю историю чата?")
        yes, no = st.columns(2)
        if yes.button("Очистить", key="chat_clear_yes", type="primary"):
            st.session_state["chat_messages"] = []
            st.session_state["chat_partial"] = ""
            st.rerun()
        no.button("Отмена", key="chat_clear_no")

    # Если прошлый прогон был прерван (например, «Стоп») — сохраняем хвост ответа
    partial = st.session_state.get("chat_partial", "")
    if partial:
        st.session_state["chat_partial"] = ""
        _append_assistant(partial, time.monotonic(), stopped=True)

    messages = st.session_state["chat_messages"]
    need_response = bool(st.session_state.pop("chat_need_response", False))

    # Блок истории сверху: сообщения по порядку + ответ, если он запрошен.
    # Внутри streamlit сам прокручивает к последнему сообщению (scroll-to-bottom).
    if messages or need_response:
        with st.container(**({"height": _CHAT_HISTORY_PX} if _CONTAINER_HEIGHT_SUPPORTED else {})):
            last_idx = len(messages) - 1
            for idx, msg in enumerate(messages):
                with st.chat_message(msg["role"]):
                    if msg["role"] == "assistant":
                        thinking, answer = detect_thinking_block(msg["content"])
                        if thinking:
                            with st.expander("Рассуждения модели", expanded=False):
                                st.markdown(thinking)
                            st.markdown(answer)
                        else:
                            st.markdown(msg["content"])
                        meta = msg.get("meta")
                        if meta:
                            st.markdown(
                                f'<div class="msg-meta">{meta["sec"]} с · ~{meta["tokens"]} ток.</div>',
                                unsafe_allow_html=True,
                            )
                        if idx == last_idx and not need_response:
                            st.button(
                                "",
                                icon="🔄",
                                key="chat_regen",
                                help="Удалить последний ответ и ответить заново",
                                disabled=not st.session_state.get("llm_model"),
                                on_click=_mark_regen,
                            )
                    else:
                        st.markdown(msg.get("display", msg["content"]))

            if need_response and not (messages and messages[-1]["role"] == "user"):
                need_response = False
            if need_response:
                if not st.session_state.get("llm_model"):
                    st.error("Сначала выберите модель в боковой панели.")
                else:
                    # кнопка должна отрендериться ДО стрима — CSS приподнимет её
                    # в правый нижний угол, рядом с полем ввода
                    st.button(
                        "",
                        icon="⏹",
                        key="chat_stop",
                        help="Остановить генерацию",
                        on_click=_set_cancel,
                    )
                    if _stream_assistant():
                        st.rerun()

    # Поле ввода — сразу под историей
    has_input, message, files = _chat_input_widget()
    if has_input:
        _append_user_message(message or "Проанализируй прикреплённые документы.", files)
        st.rerun()


# ──────────────────────────────────────────────
# ТАБ 2: Анализ документов
# ──────────────────────────────────────────────
@st.fragment
def run_doc_analysis() -> None:
    st.markdown("#### Анализ документов")
    st.caption("Загрузите документы и опишите задачу. Система разобьёт текст на части и составит отчёт.")

    st.selectbox(
        "Шаблон задачи",
        list(DOC_PRESETS),
        key="doc_preset",
        on_change=_apply_task_preset,
        args=(DOC_PRESETS, "doc_preset", "doc_user_goal"),
        help="Подставляет типовую формулировку в поле задачи — можно править",
    )

    user_goal = st.text_area(
        "Что нужно проанализировать?",
        height=80,
        key="doc_user_goal",
        placeholder="Например: найти все упоминания сроков, выделить ключевые риски...",
    )

    analysis_mode = st.selectbox(
        "Режим анализа",
        options=["general", "spike"],
        format_func=lambda m: {
            "general": "Общий анализ документа",
            "spike": "Всплеск обращений (транскрипты диалогов)",
        }[m],
        key="doc_analysis_mode",
    )

    uploaded_docs = st.file_uploader(
        "Загрузить документы",
        type=["pdf", "docx", "xlsx", "txt"],
        accept_multiple_files=True,
        key="doc_uploader",
    )

    with st.expander("Параметры дробления", expanded=False):
        doc_chunk_size = st.number_input(
            "Размер чанка",
            min_value=1000,
            max_value=100000,
            step=500,
            key="doc_chunk_size",
            help="Символов в одном чанке для анализа документов.",
        )
        _render_chunk_guidance(selected_chunk_size=int(doc_chunk_size))
        total_len = sum(len(d["text"] or "") for d in st.session_state.get("doc_attached_files", []))
        if total_len:
            st.caption(f"≈ {-(-total_len // max(1, int(doc_chunk_size)))} чанков при выбранном размере")

    if uploaded_docs:
        st.session_state["doc_attached_files"] = _extract_files_text(list(uploaded_docs))
        if st.session_state["doc_attached_files"]:
            names = ", ".join(d["name"] for d in st.session_state["doc_attached_files"])
            st.caption(f"Загружено: {names}")
            with st.expander("Предпросмотр текста", expanded=False):
                for d in st.session_state["doc_attached_files"]:
                    st.markdown(f"**{d['name']}**")
                    st.code((d["text"] or "")[:800] or "— пусто —", language="text")

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        start_clicked = st.button("Начать", type="primary", key="doc_start")
    with col2:
        if st.button("Стоп", key="doc_stop"):
            _set_cancel()

    if start_clicked:
        if not user_goal.strip():
            st.warning("Опишите задачу анализа.")
        elif not st.session_state.get("doc_attached_files"):
            st.warning("Загрузите хотя бы один документ.")
        elif not st.session_state.get("llm_model"):
            st.error("Выберите модель в боковой панели.")
        else:
            _start_doc_pipeline(user_goal=user_goal, analysis_mode=analysis_mode)

    report = st.session_state.get("doc_report")
    if report:
        st.markdown("### Результат анализа")
        _render_report(report=report, file_stem="Анализ_документов")


def _start_doc_pipeline(*, user_goal: str, analysis_mode: str) -> None:
    cancel_check = _cancel_check
    _reset_cancel()

    docs = st.session_state["doc_attached_files"]
    full_text = _build_docs_block(docs).strip()
    if not full_text:
        st.warning("Не удалось собрать текст из документов.")
        return

    llm = build_llm()
    doc_chunk_size = int(st.session_state.get("doc_chunk_size", DOC_CHUNK_SIZE))
    chunking_settings = ChunkingSettings(
        chunk_size=doc_chunk_size,
        chunk_overlap=DOC_CHUNK_OVERLAP,
        split_strategy=DOC_SPLIT_STRATEGY,
        custom_separator=DOC_CUSTOM_SEPARATOR,
    )

    system_prompt = st.session_state.get("system_prompt", "") or None
    generation = _current_generation()

    progress = st.progress(0, text="Составляю план анализа…")
    status = st.empty()
    t0 = time.monotonic()

    def on_chunk_start(idx: int, total: int) -> None:
        pct = int(idx / total * 100)
        elapsed = int(time.monotonic() - t0)
        eta = _eta_hint(elapsed, idx, total)
        progress.progress(min(99, pct), text=f"Часть {idx}/{total} · {elapsed} с{eta}")
        status.write(f"Анализирую часть {idx}/{total}...")

    try:
        result = run_chunked_analysis(
            llm=llm,
            model=st.session_state["llm_model"],
            system_prompt=system_prompt,
            analysis_mode=analysis_mode,
            user_goal=user_goal,
            full_text=full_text,
            chunking_settings=chunking_settings,
            generation=generation,
            cancel_check=cancel_check,
            on_chunk_start=on_chunk_start,
        )

        progress.progress(100, text="Готово")
        status.empty()

        _save_report("doc_report", result)
        st.rerun()

    except AnalysisCancelled:
        status.empty()
        st.info("Анализ остановлен")
    except Exception as e:
        status.empty()
        st.error(f"Ошибка анализа: {friendly_llm_error(e)}")


# ──────────────────────────────────────────────
# ТАБ 3: Анализ звонков
# ──────────────────────────────────────────────
@st.fragment
def run_calls_analysis() -> None:
    st.markdown("#### Анализ звонков")
    st.caption("Загрузите WAV-файлы. Система транскрибирует их и проведёт анализ.")

    st.selectbox(
        "Шаблон задачи",
        list(CALLS_PRESETS),
        key="calls_preset",
        on_change=_apply_task_preset,
        args=(CALLS_PRESETS, "calls_preset", "calls_user_goal"),
        help="Подставляет типовую формулировку в поле задачи — можно править",
    )

    user_goal = st.text_area(
        "Что нужно найти в звонках?",
        height=80,
        key="calls_user_goal",
        placeholder="Например: определить причины обращений, найти перенаправления...",
    )

    uploaded_wavs = st.file_uploader(
        "Загрузить записи (WAV)",
        type=["wav"],
        accept_multiple_files=True,
        key="calls_uploader",
    )

    with st.expander("Параметры дробления", expanded=False):
        calls_chunk_size = st.number_input(
            "Размер чанка",
            min_value=1000,
            max_value=100000,
            step=500,
            key="calls_chunk_size",
            help="Символов в одном чанке для анализа звонков.",
        )
        _render_chunk_guidance(selected_chunk_size=int(calls_chunk_size))

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        if st.button("Начать", type="primary", key="calls_start"):
            if not uploaded_wavs:
                st.warning("Загрузите WAV-файлы.")
            elif not user_goal.strip():
                st.warning("Опишите цель анализа.")
            elif not st.session_state.get("llm_model"):
                st.error("Выберите модель в боковой панели.")
            else:
                _start_calls_pipeline(
                    user_goal=user_goal,
                    uploaded_wavs=list(uploaded_wavs),
                )
    with col2:
        if st.button("Стоп", key="calls_stop"):
            _set_cancel()

    report = st.session_state.get("calls_report")
    if report:
        st.markdown("### Результат анализа")
        _render_report(report=report, file_stem="Анализ_звонков")


def _start_calls_pipeline(
    *,
    user_goal: str,
    uploaded_wavs: list[Any],
) -> None:
    cancel_check = _cancel_check
    _reset_cancel()

    llm = build_llm()
    endpoint = settings.TRANSCRIBE_URL
    file_field = settings.TRANSCRIBE_FILE_FIELD

    progress = st.progress(0, text="Транскрибация…")
    status = st.empty()

    transcribe_client = TranscribeClient(endpoint=endpoint, timeout_sec=int(settings.LLM_TIMEOUT_SEC))

    transcripts: list[dict] = []
    try:
        total_files = len(uploaded_wavs)
        for i, f in enumerate(uploaded_wavs, start=1):
            if cancel_check():
                st.info("Остановлено")
                return

            filename = getattr(f, "name", f"audio_{i}.wav")
            file_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()

            status.write(f"Транскрибация {i}/{total_files}: {filename}")
            pct = int(i / total_files * 30)
            progress.progress(pct, text=f"Транскрибация {i}/{total_files}…")

            try:
                resp = transcribe_client.transcribe_wav(
                    file_bytes=file_bytes,
                    filename=filename,
                    file_field=file_field,
                    cancel_check=cancel_check,
                )
            except CancelledError:
                raise
            except Exception as e:
                progress.empty()
                st.error(f"Ошибка транскрибации «{filename}»: {friendly_llm_error(e)}")
                return
            transcripts.append({"dialogue_id": resp.dialogue_id, "transcript": resp.transcript})
    except CancelledError:
        st.info("Остановлено во время транскрибации")
        return

    combined_text = "\n\n".join(
        f"{t['dialogue_id']}\n----Транскрибация----\n{(t['transcript'] or '').strip()}"
        for t in transcripts
    ).strip()

    if not combined_text:
        st.error("Не удалось получить транскрипты.")
        return

    system_prompt = st.session_state.get("system_prompt", "") or None
    generation = _current_generation()
    calls_chunk_size = int(st.session_state.get("calls_chunk_size", CALLS_CHUNK_SIZE))

    chunking_settings = ChunkingSettings(
        chunk_size=calls_chunk_size,
        chunk_overlap=CALLS_CHUNK_OVERLAP,
        split_strategy=CALLS_SPLIT_STRATEGY,
        custom_separator=CALLS_CUSTOM_SEPARATOR,
    )

    status.write("Составляю план анализа…")
    progress.progress(35, text="Планирование…")
    t0 = time.monotonic()

    def on_chunk_start(idx: int, total: int) -> None:
        pct = 35 + int(idx / total * 60)
        elapsed = int(time.monotonic() - t0)
        eta = _eta_hint(elapsed, idx, total)
        progress.eta = _eta_hint(elapsed, idx, total)
        progress(min(99, pct), text=f"Часть {idx}/{total} · {elapsed} с{eta}")
        status.write(f"Анализирую часть {idx}/{total}...")

    final_placeholder = st.empty()

    def on_final_stream(text_so_far: str) -> None:
        final_placeholder.markdown(text_so_far)

    try:
        result = run_chunked_analysis(
            llm=llm,
            model=st.session_state["llm_model"],
            system_prompt=system_prompt,
            analysis_mode="spike",
            user_goal=user_goal,
            full_text=combined_text,
            chunking_settings=chunking_settings,
            generation=generation,
            cancel_check=cancel_check,
            on_chunk_start=on_chunk_start,
            final_stream_callback=on_final_stream,
        )

        progress.progress(100, text="Готово")
        status.empty()
        final_placeholder.empty()

        _save_report("calls_report", result)
        st.rerun()

    except AnalysisCancelled:
        status.empty()
        st.info("Анализ остановлен")
    except CancelledError:
        status.empty()
        st.info("Остановлено")
    except Exception as e:
        status.empty()
        st.error(f"Ошибка анализа звонков: {friendly_llm_error(e)}")


# ──────────────────────────────────────────────
# ТАБ 4: Транскрибация в Word
# ──────────────────────────────────────────────
@st.fragment
def run_transcription_export() -> None:
    st.markdown("#### Транскрибация диалогов в Word")
    st.caption(
        "Загрузите WAV-файлы. Сервис выполнит транскрибацию по порядку и соберёт единый Word-документ."
    )

    uploaded_wavs = st.file_uploader(
        "Загрузить записи (WAV)",
        type=["wav"],
        accept_multiple_files=True,
        key="transcribe_export_uploader",
    )

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        start_clicked = st.button("Начать", type="primary", key="transcribe_export_start")
    with col2:
        if st.button("Стоп", key="transcribe_export_stop"):
            _set_cancel()

    saved = st.session_state.get("export_docx")
    if saved:
        st.success(f"Готово: обработано файлов — {saved['count']}")
        if saved["failed"]:
            st.warning(
                "Не удалось транскрибировать некоторые файлы: "
                + ", ".join(saved["failed"])
                + ". Они пропущены и не включены в Word-файл."
            )
        st.download_button(
            label="Скачать .docx",
            data=saved["data"],
            file_name=f"Транскрибация_диалогов_{saved['timestamp']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_transcriptions_docx",
        )
        if saved.get("transcripts"):
            with st.expander("Предпросмотр транскриптов", expanded=False):
                for t in saved["transcripts"]:
                    st.markdown(f"**{t['filename']}**")
                    st.code(t["transcript"] or "— пусто —", language="text")

    if not start_clicked:
        return

    if not uploaded_wavs:
        st.warning("Загрузите хотя бы один WAV-файл.")
        return

    _start_transcription_export_pipeline(uploaded_wavs=list(uploaded_wavs))


def _start_transcription_export_pipeline(*, uploaded_wavs: list[Any]) -> None:
    cancel_check = _cancel_check
    _reset_cancel()

    endpoint = settings.TRANSCRIBE_URL
    file_field = settings.TRANSCRIBE_FILE_FIELD
    transcribe_client = TranscribeClient(endpoint=endpoint, timeout_sec=int(settings.LLM_TIMEOUT_SEC))

    progress = st.progress(0, text="Транскрибация файлов…")
    status = st.empty()

    transcripts: list[dict[str, str]] = []
    failed_files: list[str] = []
    total_files = len(uploaded_wavs)

    try:
        for i, f in enumerate(uploaded_wavs, start=1):
            if cancel_check():
                st.info("Обработка остановлена")
                return

            filename = getattr(f, "name", f"audio_{i}.wav")
            file_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()

            status.write(f"Транскрибация {i}/{total_files}: {filename}")
            progress.progress(int(i / total_files * 100), text=f"Транскрибация {i}/{total_files}…")

            try:
                resp = transcribe_client.transcribe_wav(
                    file_bytes=file_bytes,
                    filename=filename,
                    file_field=file_field,
                    cancel_check=cancel_check,
                )
            except CancelledError:
                raise
            except Exception:
                failed_files.append(filename)
                continue

            transcripts.append({"filename": filename, "transcript": (resp.transcript or "").strip()})
    except CancelledError:
        st.info("Обработка остановлена")
        return

    if not transcripts:
        status.empty()
        if failed_files:
            st.warning(
                "Некоторые файлы не удалось транскрибировать: "
                + ", ".join(failed_files)
                + ". Проверьте сервис транскрибации или попробуйте позже."
            )
        st.error("Не удалось получить ни одной успешной транскрибации.")
        return

    try:
        docx_file = transcriptions_to_docx(transcripts)
    except Exception as e:
        st.error(f"Транскрибация получена, но не удалось сформировать Word файл: {e}")
        return

    status.empty()
    progress.empty()

    st.session_state["export_docx"] = {
        "data": docx_file.getvalue(),
        "failed": list(failed_files),
        "count": len(transcripts),
        "transcripts": [
            {"filename": t.get("filename", ""), "transcript": (t.get("transcript") or "")[:500]}
            for t in transcripts
        ],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    }
    st.rerun()


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main() -> None:
    _auto_load_models()

    # Sidebar — модель и системный промпт
    render_sidebar()

    # Табы
    tabs = st.tabs(["Чат", "Документы", "Звонки", "Транскрибация"])
    with tabs[0]:
        run_chat()
    with tabs[1]:
        run_doc_analysis()
    with tabs[2]:
        run_calls_analysis()
    with tabs[3]:
        run_transcription_export()


main()
