from chunking import ChunkingSettings, make_chunks
from llm_client import GenerationParams, LLMClient


def test_split_by_chars_with_overlap():
    text = "x" * 100
    chunks = make_chunks(text, ChunkingSettings(chunk_size=40, chunk_overlap=10, split_strategy="chars"))
    assert len(chunks) >= 3
    assert all(len(c) <= 40 for c in chunks)


def test_split_by_paragraphs():
    text = "Абзац первый.\n\nАбзац второй.\n\nАбзац третий."
    chunks = make_chunks(text, ChunkingSettings(chunk_size=1000, chunk_overlap=0, split_strategy="paragraphs"))
    joined = "\n\n".join(chunks)
    for part in ("первый", "второй", "третий"):
        assert part in joined


def test_split_by_separator_falls_back_to_paragraphs():
    text = "раз\n\nдва\n\nтри"
    chunks = make_chunks(
        text,
        ChunkingSettings(chunk_size=1000, chunk_overlap=0, split_strategy="separator", custom_separator=r"={3,}"),
    )
    assert chunks  # не пусто, фолбэк на абзацы


def test_empty_text_returns_no_chunks():
    assert make_chunks("", ChunkingSettings()) == []


def test_overlap_is_clamped_below_chunk_size():
    # overlap > 40% от размера чанка должен быть уменьшен, а не уходить в бесконечный цикл
    text = "word " * 2000
    chunks = make_chunks(text, ChunkingSettings(chunk_size=100, chunk_overlap=9999, split_strategy="chars"))
    assert chunks


def test_generation_params_defaults():
    params = GenerationParams()
    assert params.temperature == 0.2
    assert params.top_p is None
    assert params.max_tokens is None


def test_openai_payload_includes_optional_params():
    payload = LLMClient._openai_payload(
        "m",
        [{"role": "user", "content": "hi"}],
        stream=True,
        params=GenerationParams(temperature=0.5, top_p=0.9, max_tokens=128),
    )
    assert payload["temperature"] == 0.5
    assert payload["top_p"] == 0.9
    assert payload["max_tokens"] == 128
    assert payload["stream"] is True


def test_openai_payload_omits_none_params():
    payload = LLMClient._openai_payload(
        "m", [{"role": "user", "content": "hi"}], stream=False, params=GenerationParams()
    )
    assert "top_p" not in payload
    assert "max_tokens" not in payload


def test_ollama_payload_maps_max_tokens_to_num_predict():
    payload = LLMClient._ollama_payload(
        "m",
        [{"role": "user", "content": "hi"}],
        stream=False,
        params=GenerationParams(temperature=0.3, top_p=0.8, max_tokens=64),
    )
    options = payload["options"]
    assert options["temperature"] == 0.3
    assert options["top_p"] == 0.8
    assert options["num_predict"] == 64


def test_normalize_provider():
    assert LLMClient.normalize_provider("Ollama") == "ollama"
    assert LLMClient.normalize_provider("  vLLM ") == "vllm"
    assert LLMClient.normalize_provider("openrouter") == "custom"


def test_extract_context_window_from_nested_json():
    data = {"details": {"unknown": [{"max_model_len": "32768"}]}}
    assert LLMClient._extract_context_window(data) == 32768
