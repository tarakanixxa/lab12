from pathlib import Path
import duckdb, pandas as pd, json
ROOT=Path(__file__).resolve().parents[1]
con=duckdb.connect(str(ROOT/"data"/"metal_detail.duckdb"), read_only=True)
queries = {
"01_rollup_month_machine": """
SELECT d.year_num, d.month_num, m.machine_name, SUM(f.quantity_good) AS good_units
FROM fact_production f JOIN dim_date d USING(date_key) JOIN dim_machine m USING(machine_key)
GROUP BY ROLLUP(d.year_num, d.month_num, m.machine_name)
ORDER BY d.year_num, d.month_num, m.machine_name
""",
"02_grouping_sets": """
SELECT d.year_num, m.machine_type, SUM(f.machine_minutes) AS machine_minutes
FROM fact_production f JOIN dim_date d USING(date_key) JOIN dim_machine m USING(machine_key)
GROUP BY GROUPING SETS ((d.year_num,m.machine_type),(d.year_num),(m.machine_type),())
ORDER BY d.year_num, m.machine_type
""",
"03_slice_2025": """
SELECT p.product_name, SUM(f.quantity_total) AS produced
FROM fact_production f JOIN dim_date d USING(date_key) JOIN dim_product p USING(product_key)
WHERE d.year_num=2025 GROUP BY p.product_name ORDER BY produced DESC
""",
"04_dice_turning_cnc_morning": """
SELECT m.machine_name, p.product_name, SUM(f.quantity_good) AS good_units
FROM fact_production f JOIN dim_machine m USING(machine_key)
JOIN dim_product p USING(product_key)
JOIN dim_operation_taxonomy o USING(operation_key)
JOIN dim_shift s USING(shift_key)
WHERE m.machine_type='CNC lathe' AND o.subclass_label='Точіння' AND s.shift_name='Ранкова'
GROUP BY m.machine_name,p.product_name ORDER BY good_units DESC
""",
"05_pivot_shift": """
PIVOT (SELECT s.shift_name, SUM(f.quantity_good) AS good_units
       FROM fact_production f JOIN dim_shift s USING(shift_key)
       GROUP BY s.shift_name)
ON shift_name IN ('Ранкова','Вечірня','Нічна') USING SUM(good_units)
""",
"06_running_total": """
WITH monthly AS (
 SELECT d.year_num,d.month_num,SUM(f.quantity_good) good_units
 FROM fact_production f JOIN dim_date d USING(date_key)
 GROUP BY d.year_num,d.month_num
)
SELECT *, SUM(good_units) OVER (PARTITION BY year_num ORDER BY month_num
 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_good
FROM monthly ORDER BY year_num,month_num
""",
"07_rank_machines": """
WITH x AS (
 SELECT m.machine_name, SUM(f.quantity_good) good_units
 FROM fact_production f JOIN dim_machine m USING(machine_key)
 GROUP BY m.machine_name
)
SELECT *, RANK() OVER(ORDER BY good_units DESC) AS production_rank
FROM x ORDER BY production_rank
""",
"08_moving_average": """
WITH monthly AS (
 SELECT d.year_num,d.month_num,SUM(f.downtime_minutes) downtime
 FROM fact_production f JOIN dim_date d USING(date_key)
 GROUP BY d.year_num,d.month_num
)
SELECT *, AVG(downtime) OVER(ORDER BY year_num,month_num
 ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3m
FROM monthly ORDER BY year_num,month_num
""",
"09_taxonomy_drilldown": """
SELECT o.class_label,o.subclass_label,o.operation_label,
       SUM(f.machine_minutes) machine_minutes, SUM(f.quantity_total) units
FROM fact_production f JOIN dim_operation_taxonomy o USING(operation_key)
GROUP BY o.class_label,o.subclass_label,o.operation_label
ORDER BY o.class_label,o.subclass_label,o.operation_label
"""
}
out=[]
for name,sql in queries.items():
    df=con.execute(sql).df()
    df.to_csv(ROOT/"data"/f"{name}.csv",index=False)
    out.append({"name":name,"sql":sql,"rows":len(df),"preview":df.head(8).to_dict(orient="records")})
# Independent pandas cross-checks
fact=con.execute("SELECT * FROM fact_production").df()
d=con.execute("SELECT date_key,year_num,month_num FROM dim_date").df()
m=con.execute("SELECT machine_key,machine_name FROM dim_machine").df()
joined=fact.merge(d,on="date_key").merge(m,on="machine_key")

p1 = joined.groupby(
    ["year_num", "month_num"], as_index=False
)["quantity_good"].sum()

sql1 = con.execute("""
SELECT d.year_num, d.month_num,
       SUM(f.quantity_good) AS quantity_good
FROM fact_production f
JOIN dim_date d USING(date_key)
GROUP BY d.year_num, d.month_num
ORDER BY 1, 2
""").df()

p1 = p1.sort_values(
    ["year_num", "month_num"]
).reset_index(drop=True)

sql1 = sql1.sort_values(
    ["year_num", "month_num"]
).reset_index(drop=True)

check1 = (
    p1[["year_num", "month_num"]].astype("int64").equals(
        sql1[["year_num", "month_num"]].astype("int64")
    )
    and p1.shape == sql1.shape
    and (p1["quantity_good"].astype("int64").to_numpy()
         == sql1["quantity_good"].astype("int64").to_numpy()).all()
)

p2 = joined.groupby(
    "machine_name", as_index=False
)["quantity_good"].sum()

sql2 = con.execute("""
SELECT m.machine_name,
       SUM(f.quantity_good) AS quantity_good
FROM fact_production f
JOIN dim_machine m USING(machine_key)
GROUP BY m.machine_name
ORDER BY m.machine_name
""").df()

p2 = p2.sort_values(
    "machine_name"
).reset_index(drop=True)

sql2 = sql2.sort_values(
    "machine_name"
).reset_index(drop=True)

check2 = (
    p2["machine_name"].astype(str).equals(
        sql2["machine_name"].astype(str)
    )
    and p2.shape == sql2.shape
    and (p2["quantity_good"].astype("int64").to_numpy()
         == sql2["quantity_good"].astype("int64").to_numpy()).all()
)

(ROOT/"data"/"pandas_validation.json").write_text(json.dumps({"monthly_good_units_match":bool(check1),"machine_good_units_match":bool(check2)},indent=2),encoding="utf-8")
(ROOT/"data"/"olap_execution_summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
con.close()
print("Executed",len(queries),"OLAP queries; pandas validations:",check1,check2)
