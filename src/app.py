"""
LLM Service — чат, анализ документов, анализ звонков.
UI в стиле ChatGPT с сине-фиолетовой темой.
"""
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from analyzer import AnalysisCancelled, run_chunked_analysis
from chunking import ChunkingSettings
from config import settings
from document_extractors import extract_text
from llm_client import CancelledError, LLMClient
from transcribe_client import CancelledError as TranscribeCancelledError
from transcribe_client import TranscribeClient

# ──────────────────────────────────────────────
# Параметры анализа (зашиты в код, пользователь не видит)
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

# ──────────────────────────────────────────────
# Streamlit page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI Ассистент",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)

# ──────────────────────────────────────────────
# Кастомные CSS-стили (сине-фиолетовая тема)
# ──────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Общий фон ── */
.stApp {
    background: linear-gradient(160deg, #0F0A1E 0%, #1a1145 50%, #0d1b3e 100%);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E1640 0%, #0F0A1E 100%) !important;
    border-right: 1px solid rgba(124, 58, 237, 0.2) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextArea label {
    color: #A78BFA !important;
    font-weight: 600 !important;
}

/* ── Чат-сообщения ── */
.stChatMessage {
    border-radius: 16px !important;
    margin-bottom: 8px !important;
}
[data-testid="stChatMessageContent"] {
    border-radius: 16px !important;
}

/* ── Кнопки (обычные) ── */
.stButton > button {
    background: linear-gradient(135deg, #7C3AED, #4F46E5) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 4px 14px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #6D28D9, #4338CA) !important;
    box-shadow: 0 4px 16px rgba(124, 58, 237, 0.35) !important;
    transform: translateY(-1px) !important;
}

/* ── Кнопка primary (Начать анализ) ── */
.stButton > button[kind="primary"] {
    padding: 6px 20px !important;
    font-size: 0.9rem !important;
}

/* ── Инпуты ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(30, 22, 64, 0.6) !important;
    border: 1px solid rgba(124, 58, 237, 0.3) !important;
    border-radius: 12px !important;
    color: #E2D9F3 !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background: rgba(30, 22, 64, 0.6) !important;
    border: 1px solid rgba(124, 58, 237, 0.3) !important;
    border-radius: 16px !important;
}
[data-testid="stChatInput"] textarea {
    color: #E2D9F3 !important;
}

/* ── Табы ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(30, 22, 64, 0.5);
    border-radius: 14px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    color: #A78BFA !important;
    font-weight: 600 !important;
    padding: 8px 24px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #7C3AED, #4F46E5) !important;
    color: #fff !important;
}

/* ── Expander (toggle) ── */
.streamlit-expanderHeader {
    background: rgba(30, 22, 64, 0.6) !important;
    border-radius: 12px !important;
    color: #A78BFA !important;
    font-weight: 600 !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #7C3AED, #4F46E5) !important;
    border-radius: 8px !important;
}

/* ── File uploader — компактный ── */
[data-testid="stFileUploader"] {
    border: 1px dashed rgba(124, 58, 237, 0.3) !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;
}
[data-testid="stFileUploader"] section {
    padding: 0 !important;
}
[data-testid="stFileUploader"] section > div {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
/* Скрыть большой текст drag-and-drop */
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    padding: 8px !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div > div {
    font-size: 0.8rem !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] small {
    font-size: 0.7rem !important;
}

/* ── Скроллбар ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(124, 58, 237, 0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124, 58, 237, 0.5); }
</style>
""",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
def _init_session_state() -> None:
    st.session_state.setdefault("cancel", False)
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("chat_attached_docs", [])
    st.session_state.setdefault("doc_attached_files", [])
    st.session_state.setdefault("model_list", [])
    st.session_state.setdefault("ollama_api_type", None)
    st.session_state.setdefault("llm_provider", "ollama")
    st.session_state.setdefault("llm_base_url", settings.DEFAULT_OLLAMA_URL)
    st.session_state.setdefault("llm_model", "")
    st.session_state.setdefault("system_prompt", "")
    st.session_state.setdefault("temperature", DEFAULT_TEMPERATURE)
    st.session_state.setdefault("models_loaded", False)


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


def _extract_files_text(uploaded_files: list[Any]) -> list[dict]:
    extracted: list[dict] = []
    for f in uploaded_files:
        if f is None:
            continue
        file_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()
        file_name = getattr(f, "name", "file")
        try:
            text = extract_text(file_name, file_bytes)
            if not text.strip():
                st.warning(f'Файл «{file_name}» пуст или не удалось извлечь текст.')
                continue
            extracted.append({"name": file_name, "text": text})
        except Exception as e:
            st.warning(f'Ошибка извлечения «{file_name}»: {e}')
    return extracted


def _build_docs_block(docs: list[dict]) -> str:
    return "\n\n".join(f"--- Документ: {d['name']} ---\n{d['text']}" for d in docs)


def _build_chat_user_prompt(message: str, attached_docs: list[dict]) -> str:
    if not attached_docs:
        return message
    return message + "\n\n" + _build_docs_block(attached_docs)


def _detect_thinking_block(text: str) -> tuple[str, str]:
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
        r"\s*\*{0,2}(?:Рассуждени[ея]|Thinking|Reasoning|Мысли)\*{0,2}\s*:?\s*(.*?)(?:\n\n---|\n\n\*{0,2}(?:Ответ|Answer|Результат)\*{0,2})",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        thinking = m.group(1).strip()
        answer = text[m.end() :].strip()
        if answer:
            return thinking, answer

    return "", text


# ──────────────────────────────────────────────
# LLM helpers
# ──────────────────────────────────────────────
def refresh_models() -> None:
    provider = st.session_state["llm_provider"]
    base_url = st.session_state["llm_base_url"]
    timeout_sec = int(st.session_state.get("llm_timeout_sec", settings.LLM_TIMEOUT_SEC))

    llm = LLMClient(provider=provider, base_url=base_url, timeout_sec=timeout_sec)
    models_info = llm.list_models()
    st.session_state["model_list"] = models_info.models
    st.session_state["ollama_api_type"] = models_info.api_type
    st.session_state["models_loaded"] = True
    if models_info.models:
        if not st.session_state.get("llm_model") or st.session_state["llm_model"] not in models_info.models:
            st.session_state["llm_model"] = models_info.models[0]


def build_llm() -> LLMClient:
    return LLMClient(
        provider=st.session_state["llm_provider"],
        base_url=st.session_state["llm_base_url"],
        timeout_sec=int(st.session_state.get("llm_timeout_sec", settings.LLM_TIMEOUT_SEC)),
        ollama_api_type=st.session_state.get("ollama_api_type"),
    )


# ──────────────────────────────────────────────
# Sidebar — выбор модели и системный промпт
# ──────────────────────────────────────────────
def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🤖 Настройки модели")

        # Выбор провайдера
        provider_options = ["Ollama", "vLLM"]
        current_provider = st.session_state.get("llm_provider", "ollama")
        provider_idx = 0 if current_provider == "ollama" else 1
        
        selected_provider = st.selectbox(
            "Провайдер",
            provider_options,
            index=provider_idx,
            key="sidebar_provider_select",
        )
        
        # Автоматически обновляем провайдер и URL при смене
        new_provider = "ollama" if selected_provider == "Ollama" else "vllm"
        if new_provider != st.session_state.get("llm_provider"):
            st.session_state["llm_provider"] = new_provider
            # Автоматически обновляем base_url в зависимости от провайдера
            if new_provider == "ollama":
                st.session_state["llm_base_url"] = settings.DEFAULT_OLLAMA_URL
            else:
                st.session_state["llm_base_url"] = settings.DEFAULT_VLLM_URL
            # Сбрасываем информацию о моделях
            st.session_state["models_loaded"] = False
            st.session_state["model_list"] = []
            st.session_state["llm_model"] = ""
            # Автоматически загружаем модели для нового провайдера
            try:
                refresh_models()
            except Exception:
                pass

        # Отображаем текущий URL
        st.caption(f"🔗 URL: {st.session_state.get('llm_base_url', 'не установлен')}")

        st.divider()

        # Выбор модели
        model_list = st.session_state.get("model_list", []) or []
        if model_list:
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

        if st.button("🔄 Обновить список моделей", key="sidebar_refresh"):
            try:
                refresh_models()
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка: {e}")

        st.divider()

        # Системный промпт
        st.session_state["system_prompt"] = st.text_area(
            "Системный промпт",
            value=st.session_state.get("system_prompt", "") or "",
            height=120,
            key="sidebar_system_prompt",
            placeholder="Введите системный промпт (необязательно)...",
        )

        st.divider()
        st.caption("Подключение настраивается через .env файл.")


# ──────────────────────────────────────────────
# Автозагрузка моделей при первом запуске
# ──────────────────────────────────────────────
def _auto_load_models() -> None:
    if not st.session_state.get("models_loaded"):
        try:
            refresh_models()
        except Exception:
            pass


# ──────────────────────────────────────────────
# ТАБ 1: Чат (стиль ChatGPT)
# ──────────────────────────────────────────────
def run_chat() -> None:
    # Компактные кнопки управления
    btn_cols = st.columns([1, 1, 6])
    with btn_cols[0]:
        if st.button("🗑️ Очистить", key="chat_clear"):
            st.session_state["chat_messages"] = []
            st.session_state["chat_attached_docs"] = []
            st.rerun()
    with btn_cols[1]:
        if st.button("⏹️ Стоп", key="chat_stop"):
            _set_cancel()

    # Отображение истории
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                thinking, answer = _detect_thinking_block(msg["content"])
                if thinking:
                    with st.expander("💭 Рассуждения модели", expanded=False):
                        st.markdown(thinking)
                    st.markdown(answer)
                else:
                    st.markdown(msg["content"])
            else:
                display_text = msg.get("display", msg["content"])
                st.markdown(display_text)

    # Загрузка файлов для контекста
    uploaded_docs = st.file_uploader(
        "📎 Прикрепить документы",
        type=["pdf", "docx", "xlsx", "txt", "doc"],
        accept_multiple_files=True,
        key="chat_docs_uploader",
        label_visibility="collapsed",
    )

    if uploaded_docs:
        if not st.session_state["chat_attached_docs"]:
            st.session_state["chat_attached_docs"] = _extract_files_text(list(uploaded_docs))
            if st.session_state["chat_attached_docs"]:
                names = ", ".join(d["name"] for d in st.session_state["chat_attached_docs"])
                st.success(f"📄 Прикреплено: {names}")

    # Поле ввода
    message = st.chat_input("Напишите сообщение...")
    if message:
        if not st.session_state.get("llm_model") or st.session_state["llm_model"] == "(нет моделей)":
            st.error("Сначала выберите модель в боковой панели (☰).")
            return

        docs_block = st.session_state["chat_attached_docs"]
        full_prompt = _build_chat_user_prompt(message, docs_block)

        st.session_state["chat_messages"].append({
            "role": "user",
            "content": full_prompt,
            "display": message + (f"\n\n📎 _{len(docs_block)} документ(ов) прикреплено_" if docs_block else ""),
        })
        st.session_state["chat_attached_docs"] = []

        with st.chat_message("user"):
            st.markdown(message)

        # Стриминг ответа
        st.session_state["cancel"] = False
        llm = build_llm()

        assistant_text = ""
        try:
            system_prompt_eff = st.session_state.get("system_prompt", "") or None
            temperature_eff = float(st.session_state.get("temperature", DEFAULT_TEMPERATURE))

            # Собираем полную историю как массив messages для API
            api_messages = []
            for m in st.session_state["chat_messages"]:
                if m["role"] in ("user", "assistant"):
                    api_messages.append({"role": m["role"], "content": m["content"]})

            cancel_check = _cancel_check
            stream_gen = llm.chat_completion(
                model=st.session_state["llm_model"],
                system_prompt=system_prompt_eff,
                user_prompt="",  # не используется когда передан messages
                temperature=temperature_eff,
                stream=True,
                cancel_check=cancel_check,
                messages=api_messages,
            )

            with st.chat_message("assistant"):
                placeholder = st.empty()
                for token in stream_gen:  # type: ignore[union-attr]
                    assistant_text += token
                    placeholder.markdown(assistant_text + "▌")
                    if cancel_check():
                        break
                placeholder.markdown(assistant_text)

            st.session_state["chat_messages"].append({"role": "assistant", "content": assistant_text})
            st.rerun()

        except CancelledError:
            if assistant_text:
                st.session_state["chat_messages"].append({"role": "assistant", "content": assistant_text})
            st.info("⏹️ Генерация остановлена.")
        except Exception as e:
            st.error(f"Ошибка генерации: {e}")


# ──────────────────────────────────────────────
# ТАБ 2: Анализ документов
# ──────────────────────────────────────────────
def run_doc_analysis() -> None:
    st.markdown("#### 📄 Анализ документов")
    st.caption("Загрузите документы и опишите задачу. Система разобьёт текст на части и составит отчёт.")

    user_goal = st.text_area(
        "Что нужно проанализировать?",
        height=80,
        key="doc_user_goal",
        placeholder="Например: найти все упоминания сроков, выделить ключевые риски...",
    )

    uploaded_docs = st.file_uploader(
        "📎 Загрузить документы",
        type=["pdf", "docx", "xlsx", "txt", "doc"],
        accept_multiple_files=True,
        key="doc_uploader",
    )

    if uploaded_docs:
        st.session_state["doc_attached_files"] = _extract_files_text(list(uploaded_docs))
        if st.session_state["doc_attached_files"]:
            names = ", ".join(d["name"] for d in st.session_state["doc_attached_files"])
            st.caption(f"📄 Загружено: {names}")

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🚀 Начать", type="primary", key="doc_start"):
            if not user_goal.strip():
                st.warning("Опишите задачу анализа.")
            elif not st.session_state.get("doc_attached_files"):
                st.warning("Загрузите хотя бы один документ.")
            elif not st.session_state.get("llm_model"):
                st.error("Выберите модель в боковой панели.")
            else:
                _start_doc_pipeline(user_goal=user_goal)
    with col2:
        if st.button("⏹️ Стоп", key="doc_stop"):
            _set_cancel()


def _start_doc_pipeline(*, user_goal: str) -> None:
    cancel_check = _cancel_check
    _reset_cancel()

    docs = st.session_state["doc_attached_files"]
    full_text = "\n\n".join(f"--- Документ: {d['name']} ---\n{d['text']}" for d in docs).strip()
    if not full_text:
        st.warning("Не удалось собрать текст из документов.")
        return

    llm = build_llm()
    chunking_settings = ChunkingSettings(
        chunk_size=DOC_CHUNK_SIZE,
        chunk_overlap=DOC_CHUNK_OVERLAP,
        split_strategy=DOC_SPLIT_STRATEGY,
        custom_separator=DOC_CUSTOM_SEPARATOR,
    )

    system_prompt = st.session_state.get("system_prompt", "") or None
    temperature = float(st.session_state.get("temperature", DEFAULT_TEMPERATURE))

    progress = st.progress(0, text="📋 Составляю план анализа...")
    status = st.empty()

    def on_chunk_start(idx: int, total: int) -> None:
        pct = int(idx / total * 100)
        progress.progress(min(99, pct), text=f"📊 Часть {idx}/{total}")
        status.write(f"Анализирую часть {idx}/{total}...")

    try:
        result = run_chunked_analysis(
            llm=llm,
            model=st.session_state["llm_model"],
            system_prompt=system_prompt,
            analysis_mode="general",
            user_goal=user_goal,
            full_text=full_text,
            chunking_settings=chunking_settings,
            temperature=temperature,
            cancel_check=cancel_check,
            on_chunk_start=on_chunk_start,
        )

        progress.progress(100, text="✅ Готово!")
        status.empty()

        st.success("Анализ завершён!")

        # Отчёт на всю ширину
        st.divider()
        st.markdown(result.final_markdown)
        st.divider()

        with st.expander("🔍 Детали: план и заметки по частям", expanded=False):
            st.markdown("**План анализа:**")
            st.code(result.plan, language="text")
            for n in result.per_chunk_notes:
                st.markdown(f"**Часть {n.idx}**")
                st.code(n.notes, language="text")

    except AnalysisCancelled:
        st.info("⏹️ Анализ остановлен.")
    except Exception as e:
        st.error(f"Ошибка анализа: {e}")


# ──────────────────────────────────────────────
# ТАБ 3: Анализ звонков
# ──────────────────────────────────────────────
def run_calls_analysis() -> None:
    st.markdown("#### 📞 Анализ звонков")
    st.caption("Загрузите WAV-файлы. Система транскрибирует их и проведёт анализ.")

    user_goal = st.text_area(
        "Что нужно найти в звонках?",
        height=80,
        key="calls_user_goal",
        placeholder="Например: определить причины обращений, найти перенаправления...",
    )

    uploaded_wavs = st.file_uploader(
        "🎙️ Загрузить записи (WAV)",
        type=["wav"],
        accept_multiple_files=True,
        key="calls_uploader",
    )

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🚀 Начать", type="primary", key="calls_start"):
            if not uploaded_wavs:
                st.warning("Загрузите WAV-файлы.")
            elif not user_goal.strip():
                st.warning("Опишите цель анализа.")
            elif not st.session_state.get("llm_model"):
                st.error("Выберите модель в боковой панели.")
            else:
                _start_calls_pipeline(
                    user_goal=user_goal,
                    uploaded_wavs=uploaded_wavs,
                )
    with col2:
        if st.button("⏹️ Стоп", key="calls_stop"):
            _set_cancel()


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

    progress = st.progress(0, text="🎙️ Транскрибация...")
    status = st.empty()

    transcribe_client = TranscribeClient(endpoint=endpoint, timeout_sec=int(settings.LLM_TIMEOUT_SEC))

    transcripts: list[dict] = []
    try:
        total_files = len(uploaded_wavs)
        for i, f in enumerate(uploaded_wavs, start=1):
            if cancel_check():
                st.info("⏹️ Остановлено.")
                return

            filename = getattr(f, "name", f"audio_{i}.wav")
            file_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()

            status.write(f"🎙️ Транскрибация {i}/{total_files}: {filename}")
            pct = int(i / total_files * 30)
            progress.progress(pct, text=f"🎙️ Транскрибация {i}/{total_files}...")

            resp = transcribe_client.transcribe_wav(
                file_bytes=file_bytes,
                filename=filename,
                file_field=file_field,
                cancel_check=cancel_check,
            )
            transcripts.append({"dialogue_id": resp.dialogue_id, "transcript": resp.transcript})
    except TranscribeCancelledError:
        st.info("⏹️ Остановлено во время транскрибации.")
        return

    combined_text = "\n\n".join(
        f"{t['dialogue_id']}\n----Транскрибация----\n{(t['transcript'] or '').strip()}"
        for t in transcripts
    ).strip()

    if not combined_text:
        st.error("Не удалось получить транскрипты.")
        return

    system_prompt = st.session_state.get("system_prompt", "") or None
    temperature = float(st.session_state.get("temperature", DEFAULT_TEMPERATURE))

    chunking_settings = ChunkingSettings(
        chunk_size=CALLS_CHUNK_SIZE,
        chunk_overlap=CALLS_CHUNK_OVERLAP,
        split_strategy=CALLS_SPLIT_STRATEGY,
        custom_separator=CALLS_CUSTOM_SEPARATOR,
    )

    status.write("📋 Составляю план анализа...")
    progress.progress(35, text="📋 Планирование...")

    def on_chunk_start(idx: int, total: int) -> None:
        pct = 35 + int(idx / total * 60)
        progress.progress(min(99, pct), text=f"📊 Часть {idx}/{total}")
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
            temperature=temperature,
            cancel_check=cancel_check,
            on_chunk_start=on_chunk_start,
            final_stream_callback=on_final_stream,
        )

        progress.progress(100, text="✅ Готово!")
        status.empty()
        final_placeholder.empty()

        st.success("Анализ завершён!")

        # Отчёт на всю ширину
        st.divider()
        st.markdown(result.final_markdown)
        st.divider()

        with st.expander("🔍 Детали: план и заметки по частям", expanded=False):
            st.markdown("**План анализа:**")
            st.code(result.plan, language="text")
            for n in result.per_chunk_notes:
                st.markdown(f"**Часть {n.idx}**")
                st.code(n.notes, language="text")

    except AnalysisCancelled:
        st.info("⏹️ Анализ остановлен.")
    except CancelledError:
        st.info("⏹️ Остановлено.")
    except Exception as e:
        st.error(f"Ошибка анализа звонков: {e}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main() -> None:
    _auto_load_models()

    # Sidebar — модель и системный промпт
    render_sidebar()

    # Табы
    tabs = st.tabs(["💬 Чат", "📄 Документы", "📞 Звонки"])
    with tabs[0]:
        run_chat()
    with tabs[1]:
        run_doc_analysis()
    with tabs[2]:
        run_calls_analysis()


main()
