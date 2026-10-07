# Вклад в проект

Проект — рабочий прототип, и помощь приветствуется.

## Окружение разработки

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest ruff pre-commit
pre-commit install
```

Запуск без Docker: `streamlit run src/app.py`.

## Проверки перед PR

```bash
ruff check src tests
pytest
```

CI запускает то же самое на Python 3.11.

## Конвенции

- Python >= 3.11, `from __future__ import annotations`, type hints в публичных сигнатурах.
- Линтер — ruff (конфиг в `pyproject.toml`), ширина строки 120.
- Логика, которую можно протестировать без streamlit, выносится в обычные модули
  (`utils.py`, `chunking.py`, `analyzer.py`, ...) и покрывается pytest.
  UI-специфичное остаётся в `app.py`.
- Новые настройки окружения: добавить в `config.py` **и** `.env.example`,
  и в таблицу конфигурации README.

## Структура коммитов и PR

- Небольшие сфокусированные коммиты; описание PR — что и зачем.
- Для изменений поведения UI приложите скриншот/гифку.
- Не коммитьте `.env`, ключи API и внутренние эндпоинты — наружу только `.env.example`.

## Идеи для доработки

- Новые форматы документов (pptx, eml) и новые стратегии дробления
- Тесты транскрибации форматами, отличными от WAV (mp3/ogg — на стороне ASR-сервиса)
- Мультиязычность UI
- Страницы истории/шаблонов промптов
