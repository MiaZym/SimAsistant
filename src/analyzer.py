from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from chunking import ChunkingSettings, make_chunks  # type: ignore
from llm_client import CancelledError, LLMClient
from prompts import (
    build_chunk_prompt,
    build_compress_prompt,
    build_final_prompt,
    build_plan_prompt,
    parse_chunk_response,
    parse_plan_response,
)


class AnalysisCancelled(RuntimeError):
    pass


@dataclass
class ChunkNote:
    idx: int
    notes: str
    summary: str


@dataclass
class AnalysisResult:
    final_markdown: str
    plan: str
    per_chunk_notes: list[ChunkNote]
    cumulative_summary: str


def _should_cancel(cancel_check: Optional[Callable[[], bool]]) -> bool:
    return bool(cancel_check and cancel_check())


def run_chunked_analysis(
    *,
    llm: LLMClient,
    model: str,
    system_prompt: str | None,
    analysis_mode: str,  # general | spike
    user_goal: str,
    full_text: str,
    chunking_settings: ChunkingSettings,
    temperature: float,
    cancel_check: Optional[Callable[[], bool]] = None,
    final_stream_callback: Optional[Callable[[str], None]] = None,
    on_chunk_start: Optional[Callable[[int, int], None]] = None,
) -> AnalysisResult:
    """
    Универсальная логика:
    plan -> chunk loop (пересборка summary) -> final report
    """
    if not full_text.strip():
        raise ValueError("Входной текст пуст.")

    sample_text = full_text[:60000]
    if cancel_check and cancel_check():
        raise AnalysisCancelled()

    plan_text = llm.chat_completion(
        model=model,
        system_prompt=system_prompt,
        user_prompt=build_plan_prompt(
            analysis_mode=analysis_mode, user_goal=user_goal, sample_text=sample_text
        ),
        temperature=temperature,
        stream=False,
        cancel_check=cancel_check,
    )
    if isinstance(plan_text, str):
        plan = plan_text
    else:
        plan = "".join(list(plan_text))

    parsed_plan, params = parse_plan_response(plan)

    plan_text_out = parsed_plan or plan
    chunk_size = params.get("chunk_size") or chunking_settings.chunk_size
    chunk_overlap = params.get("chunk_overlap") or chunking_settings.chunk_overlap
    split_strategy = params.get("split_strategy") or chunking_settings.split_strategy

    final_chunk_settings = ChunkingSettings(
        chunk_size=int(chunk_size),
        chunk_overlap=int(chunk_overlap),
        split_strategy=str(split_strategy),
        custom_separator=chunking_settings.custom_separator,
    )

    chunks = make_chunks(full_text, final_chunk_settings)
    if not chunks:
        raise ValueError("Не удалось сформировать чанки.")

    cumulative_summary = ""
    per_chunk_notes: list[ChunkNote] = []

    total = len(chunks)
    for i, chunk in enumerate(chunks, start=1):
        if cancel_check and cancel_check():
            raise AnalysisCancelled()

        if on_chunk_start:
            on_chunk_start(i, total)

        user_prompt = build_chunk_prompt(
            analysis_mode=analysis_mode,
            plan=plan_text_out,
            user_goal=user_goal,
            summary=cumulative_summary,
            chunk_text=chunk,
            idx=i,
            total=total,
        )

        resp_text = llm.chat_completion(
            model=model,
            system_prompt=system_prompt,  # передаём на каждом чанке для сохранения контекста
            user_prompt=user_prompt,
            temperature=temperature,
            stream=False,
            cancel_check=cancel_check,
        )
        if not isinstance(resp_text, str):
            resp_text = "".join(list(resp_text))

        parsed = parse_chunk_response(resp_text)
        if parsed["parsed"] and parsed.get("summary"):
            cumulative_summary = parsed["summary"]

        per_chunk_notes.append(
            ChunkNote(
                idx=i,
                notes=parsed.get("notes") or parsed.get("summary") or resp_text,
                summary=parsed.get("summary") or "",
            )
        )

        # Auto-compress if summary grows too much.
        max_summary_size = int(chunk_size * 0.6)
        if cumulative_summary and len(cumulative_summary) > max_summary_size and i < total:
            if cancel_check and cancel_check():
                raise AnalysisCancelled()

            compressed = llm.chat_completion(
                model=model,
                system_prompt="",
                user_prompt=build_compress_prompt(cumulative_summary, max_summary_size),
                temperature=min(0.8, temperature),
                stream=False,
                cancel_check=cancel_check,
            )
            if isinstance(compressed, str) and len(compressed) < len(cumulative_summary):
                cumulative_summary = compressed

    final_prompt = build_final_prompt(
        analysis_mode=analysis_mode,
        user_goal=user_goal,
        summary=cumulative_summary,
        plan=plan_text_out,
    )

    # Final streaming (into UI callback)
    try:
        stream_gen = llm.chat_completion(
            model=model,
            system_prompt=system_prompt,
            user_prompt=final_prompt,
            temperature=temperature,
            stream=True,
            cancel_check=cancel_check,
        )
    except CancelledError as e:
        raise AnalysisCancelled() from e

    final_text = ""
    if isinstance(stream_gen, str):
        final_text = stream_gen
    else:
        for token in stream_gen:
            if cancel_check and cancel_check():
                raise AnalysisCancelled()
            final_text += token
            if final_stream_callback:
                final_stream_callback(final_text)

    return AnalysisResult(
        final_markdown=final_text,
        plan=plan_text_out,
        per_chunk_notes=per_chunk_notes,
        cumulative_summary=cumulative_summary,
    )

