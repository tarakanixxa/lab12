# Лабораторна робота 12 — Промисловість: виробництво валів на підприємстві «Метал-Деталь»

## Контекст
Аналітика виробничого комплексу: механічна майстерня, токарний верстат із ЧПК, матеріал — сталь 45, виріб — вал. Дані синтетичні, створені документованим генератором `etl/generate_data.py`. Вони не є фактичними даними реального підприємства.

## Швидкий запуск (Python 3.10+)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux:
source .venv/bin/activate
pip install -r requirements.txt
python etl/load.py
python src/run_olap.py
python src/semantic_layer.py
python src/text_to_sql.py
python dashboard/build_dashboard.py
```

Після запуску база `data/metal_detail.duckdb`, Parquet, звіти перевірок, JSONL-тести та `dashboard/index.html` будуть створені/оновлені. Parquet-файли генеруються скриптом `etl/load.py`, тому до першого запуску їх може ще не бути в каталозі `data/`.

## Технології
DuckDB, pandas, PyArrow, Plotly, SQLGlot, PyYAML. Усі запити виконуються локально. Text-to-SQL у демонстрації використовує контрольований набір шаблонів (mock LLM adapter), щоб проєкт працював без API-ключа. Для підключення справжньої LLM замініть `generate_sql()` у `src/text_to_sql.py`, залишивши обов'язкову валідацію SQL.

## Примітка про перевірку
Показники та приклади результатів у звіті стосуються саме синтетичного набору даних, який відтворюється фіксованим seed. Перед здачею запустіть команди у власному середовищі та додайте фактичні скриншоти запуску, якщо викладач їх вимагає.
