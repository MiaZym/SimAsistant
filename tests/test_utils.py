import requests

from utils import detect_thinking_block, format_int, friendly_llm_error


def test_detect_thinking_tag_block():
    text = "ответ\n<think>рассуждение здесь</think>"
    thinking, answer = detect_thinking_block(text)
    assert thinking == "рассуждение здесь"
    assert answer == "ответ"


def test_detect_thinking_russian_header():
    text = "Рассуждение:\nшаг 1\nшаг 2\n\n---\nИтоговый ответ"
    thinking, answer = detect_thinking_block(text)
    assert "шаг 1" in thinking
    assert answer == "Итоговый ответ"


def test_detect_thinking_no_block():
    thinking, answer = detect_thinking_block("просто ответ без рассуждений")
    assert thinking == ""
    assert answer == "просто ответ без рассуждений"


def test_friendly_error_ssl():
    exc = requests.exceptions.SSLError("cert verify failed")
    msg = friendly_llm_error(exc)
    assert "TLS" in msg
    assert "REQUESTS_CA_BUNDLE" in msg


def test_friendly_error_connection():
    exc = requests.exceptions.ConnectionError("Connection refused")
    msg = friendly_llm_error(exc)
    assert "Не удалось подключиться" in msg


def _http_error(status: int) -> requests.exceptions.HTTPError:
    resp = requests.Response()
    resp.status_code = status
    return requests.exceptions.HTTPError(f"{status}", response=resp)


def test_friendly_error_http_status_hints():
    assert "API-ключ" in friendly_llm_error(_http_error(401))
    assert "404" in friendly_llm_error(_http_error(404))
    assert "429" in friendly_llm_error(_http_error(429))
    assert "сервера" in friendly_llm_error(_http_error(503))


def test_friendly_error_unknown_falls_back_to_str():
    msg = friendly_llm_error(RuntimeError("что-то странное"))
    assert msg == "что-то странное"


def test_format_int():
    assert format_int(1234567) == "1 234 567"
