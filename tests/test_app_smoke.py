import os

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")


def _run(**session_state):
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    for key, value in session_state.items():
        at.session_state[key] = value
    at.run()
    return at


def test_app_boots_without_exceptions():
    at = _run()
    assert not at.exception, [str(e.value) for e in at.exception]


def test_saved_report_survives_rerun():
    at = _run(
        doc_report={
            "markdown": "# Отчёт\n\n- пункт",
            "plan": "план",
            "notes": [[1, "заметки"]],
            "timestamp": "20260101_000000",
        }
    )
    assert not at.exception, [str(e.value) for e in at.exception]
    texts = " ".join(str(m.value) for m in at.markdown)
    assert "Отчёт" in texts
    assert "Результат анализа" in texts


def test_chat_requires_model():
    at = _run()
    assert len(at.chat_input) == 1
    at.chat_input[0].set_value("привет")
    at.run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("модель" in str(e.value).lower() for e in at.error)


def test_dark_css_injected_by_default():
    at = _run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("ТЁМНАЯ ТЕМА" in str(m.value) for m in at.markdown)


def test_light_theme_no_dark_css():
    at = _run(ui_theme="light")
    assert not at.exception, [str(e.value) for e in at.exception]
    assert not any("ТЁМНАЯ ТЕМА" in str(m.value) for m in at.markdown)


def test_no_welcome_panel():
    at = _run()
    assert not at.exception, [str(e.value) for e in at.exception]
    texts = " ".join(str(m.value) for m in at.markdown)
    assert "Чем помочь?" not in texts


def test_export_docx_survives_rerun():
    at = _run(
        export_docx={
            "data": b"PK\x03\x04fake",
            "failed": [],
            "count": 2,
            "timestamp": "t",
        }
    )
    assert not at.exception, [str(e.value) for e in at.exception]
    assert any("Готово" in str(m.value) for m in at.success)
