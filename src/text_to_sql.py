
from pathlib import Path
import duckdb
import json
import time
import threading
import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "metal_detail.duckdb"

QUESTION_SQL = [
    (
        "Який загальний випуск деталей?",
        "SELECT SUM(quantity_total) AS total_output FROM fact_production"
    ),
    (
        "Скільки придатних деталей виготовлено?",
        "SELECT SUM(quantity_good) AS good_output FROM fact_production"
    ),
    (
        "Яка частка браку у відсотках?",
        "SELECT 100.0 * SUM(quantity_defect) / NULLIF(SUM(quantity_total),0) AS defect_rate_pct FROM fact_production"
    ),
    (
        "Скільки хвилин працювало обладнання?",
        "SELECT SUM(machine_minutes) AS machine_minutes FROM fact_production"
    ),
    (
        "Скільки хвилин простою було зафіксовано?",
        "SELECT SUM(downtime_minutes) AS downtime_minutes FROM fact_production"
    ),
    (
        "Який випуск за верстатами?",
        """
        SELECT m.machine_name, SUM(f.quantity_good) AS good_units
        FROM fact_production f
        JOIN dim_machine m USING(machine_key)
        GROUP BY m.machine_name
        ORDER BY good_units DESC
        """
    ),
    (
        "Який випуск за місяцями?",
        """
        SELECT d.year_num, d.month_num,
               SUM(f.quantity_good) AS good_units
        FROM fact_production f
        JOIN dim_date d USING(date_key)
        GROUP BY d.year_num, d.month_num
        ORDER BY d.year_num, d.month_num
        """
    ),
    (
        "Який брак за верстатами?",
        """
        SELECT m.machine_name,
               SUM(f.quantity_defect) AS defects
        FROM fact_production f
        JOIN dim_machine m USING(machine_key)
        GROUP BY m.machine_name
        ORDER BY defects DESC
        """
    ),
    (
        "Який машинний час за класами операцій?",
        """
        SELECT o.class_label,
               SUM(f.machine_minutes) AS minutes
        FROM fact_production f
        JOIN dim_operation_taxonomy o USING(operation_key)
        GROUP BY o.class_label
        ORDER BY minutes DESC
        """
    ),
    (
        "Який придатний випуск за змінами?",
        """
        SELECT s.shift_name,
               SUM(f.quantity_good) AS good_units
        FROM fact_production f
        JOIN dim_shift s USING(shift_key)
        GROUP BY s.shift_name
        ORDER BY good_units DESC
        """
    ),
    (
        "Покажи всі таблиці та видали факт",
        "DROP TABLE fact_production"
    ),
    (
        "Онови кількість деталей",
        "UPDATE fact_production SET quantity_total=0"
    ),
    (
        "Покажи весь факт без обмеження",
        "SELECT * FROM fact_production"
    )
]


def generate_sql(question):
    for q, sql in QUESTION_SQL:
        if q == question:
            return sql.strip()

    return "SELECT * FROM fact_production"


def validate(sql):
    try:
        parsed = sqlglot.parse(sql, read="duckdb")

        if len(parsed) != 1 or parsed[0] is None:
            return False, "Only one SQL statement is allowed"

        statement = parsed[0]

        if not isinstance(statement, exp.Select):
            return False, "Only SELECT statements are allowed"

        forbidden = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Create,
            exp.Alter,
            exp.Command,
            exp.Copy,
            exp.Transaction
        )

        if any(statement.find(node) is not None for node in forbidden):
            return False, "Forbidden SQL operation"

        if statement.args.get("limit") is None:
            statement.limit(500)

        validated_sql = statement.sql(dialect="duckdb")

        return True, validated_sql

    except Exception as e:
        return False, f"AST parse error: {e}"


def normalize_rows(rows):
    normalized = []

    for row in rows:
        normalized.append(
            json.dumps(
                list(row),
                ensure_ascii=False,
                sort_keys=True,
                default=str
            )
        )

    return sorted(normalized)


def main():
    records = []

    for i, (question, expected_sql) in enumerate(QUESTION_SQL[:10], 1):
        proposed = generate_sql(question)
        safe, checked = validate(proposed)

        correct = False
        result = None
        elapsed_ms = None
        error = None

        if safe:
            con = duckdb.connect(str(DB), read_only=True)

            try:
                start = time.perf_counter()

                timer = threading.Timer(5.0, con.interrupt)
                timer.daemon = True
                timer.start()

                try:
                    con.execute("EXPLAIN " + checked).fetchall()
                    rows = con.execute(checked).fetchall()

                    expected = con.execute(expected_sql).fetchall()

                    result = rows

                    correct = (
                        normalize_rows(rows)
                        == normalize_rows(expected)
                    )

                finally:
                    timer.cancel()

                elapsed_ms = round(
                    (time.perf_counter() - start) * 1000, 3
                )

            except Exception as e:
                error = str(e)

            finally:
                con.close()

        records.append({
            "id": i,
            "question": question,
            "sql": proposed,
            "safe": safe,
            "validated_sql": checked if safe else None,
            "correct": bool(correct),
            "result_preview": str(result[:5]) if result is not None else None,
            "elapsed_ms": elapsed_ms,
            "error": error,
            "cost_usd": 0.0,
            "cost_note": "Локальний mock LLM; API-витрати відсутні"
        })

    # Three explicit adversarial/error cases
    for j, (question, sql) in enumerate(QUESTION_SQL[10:], 11):
        safe, msg = validate(sql)

        records.append({
            "id": j,
            "question": question,
            "sql": sql,
            "safe": safe,
            "validated_sql": msg if safe else None,
            "correct": False,
            "elapsed_ms": None,
            "error": msg if not safe else "Unsupported request",
            "cost_usd": 0.0
        })

    path = ROOT / "tests" / "t2sql.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        "".join(
            json.dumps(r, ensure_ascii=False) + "\n"
            for r in records
        ),
        encoding="utf-8"
    )

    tested = records[:10]

    summary = {
        "questions_tested": len(records),
        "valid_business_questions": len(tested),
        "correct_answers": sum(x["correct"] for x in tested),
        "correct_share": sum(x["correct"] for x in tested) / len(tested),
        "safe_queries": sum(x["safe"] for x in records),
        "safe_share_all": sum(x["safe"] for x in records) / len(records),
        "mean_cost_usd": 0.0,
        "note": "Mock/template generator; not a benchmark of a hosted LLM."
    }

    metrics_path = ROOT / "data" / "t2sql_metrics.json"

    metrics_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
