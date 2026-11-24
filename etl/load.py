from pathlib import Path
import sys, json
import duckdb
import pandas as pd
from generate_data import generate, SEED
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB = DATA / "metal_detail.duckdb"

machines, products, ops, shifts, dates, facts = generate()
con = duckdb.connect(str(DB))
con.execute((ROOT / "sql" / "ddl.sql").read_text(encoding="utf-8"))

def df(rows, cols):
    return pd.DataFrame(rows, columns=cols)

date_rows = [(int(d.strftime("%Y%m%d")), d, d.day, d.month, d.strftime("%B"),
              (d.month-1)//3+1, d.year) for d in dates]
tables = {
 "dim_date": df(date_rows, ["date_key","full_date","day_num","month_num","month_name","quarter_num","year_num"]),
 "dim_machine": df([(x[0],x[1],x[2],x[3],x[4],x[5],x[6],"2025-01-01",None,True) for x in machines],
   ["machine_key","machine_code","machine_name","machine_type","model","workshop","complex_name","valid_from","valid_to","is_current"]),
 "dim_product": df([(x[0],x[1],x[2],x[3],x[4],x[5],"2025-01-01",None,True) for x in products],
   ["product_key","product_code","product_name","product_family","material","steel_grade","valid_from","valid_to","is_current"]),
 "dim_operation_taxonomy": df([(x[0],x[1],x[2],x[3],x[4],x[5]) for x in ops],
   ["operation_key","class_label","class_iri","subclass_label","subclass_iri","operation_label"]),
 "dim_shift": df(shifts, ["shift_key","shift_name","start_hour","end_hour"])
}
fact = df(facts, ["production_id","full_date","machine_key","product_key","operation_key","shift_key","batch_code","quantity_total","quantity_good","quantity_defect","machine_minutes","material_kg","downtime_minutes"])
fact["date_key"] = pd.to_datetime(fact["full_date"]).dt.strftime("%Y%m%d").astype(int)
fact = fact.drop(columns=["full_date"])
fact = fact[["production_id","date_key","machine_key","product_key","operation_key","shift_key","batch_code","quantity_total","quantity_good","quantity_defect","machine_minutes","material_kg","downtime_minutes"]]

con.execute("DELETE FROM fact_production")
for name, frame in tables.items():
    con.register("incoming", frame)
    con.execute(f"DELETE FROM {name}")
    con.execute(f"INSERT INTO {name} SELECT * FROM incoming")
    con.unregister("incoming")
con.register("incoming_fact", fact)
con.execute("INSERT INTO fact_production SELECT * FROM incoming_fact")
con.unregister("incoming_fact")

# Quality checks: 8 validations
checks = {}
checks["fact_rows_at_least_1000"] = con.execute("SELECT COUNT(*) >= 1000 FROM fact_production").fetchone()[0]
checks["production_id_unique"] = con.execute("SELECT COUNT(*) = COUNT(DISTINCT production_id) FROM fact_production").fetchone()[0]
checks["no_null_measures"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production WHERE quantity_total IS NULL OR machine_minutes IS NULL OR material_kg IS NULL").fetchone()[0]
checks["quantity_balance"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production WHERE quantity_total <> quantity_good + quantity_defect").fetchone()[0]
checks["nonnegative_measures"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production WHERE quantity_total < 0 OR machine_minutes < 0 OR material_kg < 0 OR downtime_minutes < 0").fetchone()[0]
checks["defect_within_total"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production WHERE quantity_defect > quantity_total").fetchone()[0]
checks["no_orphan_machine_keys"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production f LEFT JOIN dim_machine d USING(machine_key) WHERE d.machine_key IS NULL").fetchone()[0]
checks["no_orphan_date_keys"] = con.execute("SELECT COUNT(*) = 0 FROM fact_production f LEFT JOIN dim_date d USING(date_key) WHERE d.date_key IS NULL").fetchone()[0]
checks["no_orphan_product_operation_shift"] = con.execute("""
SELECT COUNT(*) = 0 FROM fact_production f
LEFT JOIN dim_product p USING(product_key)
LEFT JOIN dim_operation_taxonomy o USING(operation_key)
LEFT JOIN dim_shift s USING(shift_key)
WHERE p.product_key IS NULL OR o.operation_key IS NULL OR s.shift_key IS NULL
""").fetchone()[0]
if not all(checks.values()):
    raise RuntimeError(f"Data quality failed: {checks}")

for name in list(tables) + ["fact_production"]:
    con.execute(f"COPY {name} TO '{(DATA / (name + '.parquet')).as_posix()}' (FORMAT PARQUET)")
report = {"generator_seed": SEED, "fact_rows": len(fact), "checks": checks, "all_passed": all(checks.values()), "duckdb_version": duckdb.__version__}
(DATA / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
con.close()
print(json.dumps(report, ensure_ascii=False, indent=2))
