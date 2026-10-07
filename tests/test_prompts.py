from prompts import (
    build_chunk_prompt,
    build_final_prompt,
    build_plan_prompt,
    parse_chunk_response,
    parse_plan_response,
)


def test_parse_plan_response_markers():
    text = "мусор\n===PLAN===\n1. Пункт\n2. Пункт\n===END===\nхвост"
    plan, _ = parse_plan_response(text)
    assert "1. Пункт" in plan
    assert "мусор" not in plan


def test_parse_plan_response_no_markers_returns_raw():
    plan, _ = parse_plan_response("просто план без маркеров")
    assert plan == "просто план без маркеров"


def test_parse_chunk_response_summary_and_notes():
    text = "===SUMMARY===\nрезюме тут\n===NOTES===\nзаметки тут"
    parsed = parse_chunk_response(text)
    assert parsed["parsed"] is True
    assert parsed["summary"] == "резюме тут"
    assert parsed["notes"] == "заметки тут"


def test_parse_chunk_response_unparseable_falls_back_to_notes():
    parsed = parse_chunk_response("обычный текст без маркеров")
    assert parsed["parsed"] is False
    assert parsed["notes"] == "обычный текст без маркеров"


def test_build_chunk_prompt_spike_mentions_dialogue_id():
    prompt = build_chunk_prompt(
        analysis_mode="spike",
        plan="план",
        user_goal="цель",
        summary="",
        chunk_text="диалог 1",
        idx=1,
        total=3,
    )
    assert "dialogue_id" in prompt
    assert "чанк 1 из 3" in prompt


def test_build_plan_prompt_includes_goal_and_sample():
    prompt = build_plan_prompt(analysis_mode="general", user_goal="найти риски", sample_text="SAMPLE-ТЕКСТ")
    assert "найти риски" in prompt
    assert "SAMPLE-ТЕКСТ" in prompt
    assert "===PLAN===" in prompt


def test_build_final_prompt_includes_summary():
    prompt = build_final_prompt(analysis_mode="general", user_goal="цель", summary="ИТОГОВОЕ-РЕЗЮМЕ", plan="план")
    assert "ИТОГОВОЕ-РЕЗЮМЕ" in prompt
