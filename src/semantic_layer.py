from pathlib import Path
import duckdb, yaml, json
ROOT=Path(__file__).resolve().parents[1]
spec=yaml.safe_load((ROOT/"semantic"/"metrics.yml").read_text(encoding="utf-8"))
con=duckdb.connect(str(ROOT/"data"/"metal_detail.duckdb"),read_only=True)
def sql_for(metric_name):
    if metric_name not in spec["metrics"]:
        raise KeyError(f"Unknown metric: {metric_name}")
    return spec["metrics"][metric_name]["sql"]
results={}
for key in spec["metrics"]:
    sql=sql_for(key)
    results[key]=con.execute(sql).fetchone()[0]
# Two semantically equivalent routes: direct aggregate vs ratio of grouped aggregates
a=con.execute("SELECT 100.0*SUM(quantity_defect)/SUM(quantity_total) FROM fact_production").fetchone()[0]
b=con.execute("""SELECT 100.0*SUM(defects)/SUM(total) FROM
 (SELECT SUM(quantity_defect) defects,SUM(quantity_total) total FROM fact_production GROUP BY machine_key)""").fetchone()[0]
assert abs(a-b)<1e-9
c=con.execute("SELECT SUM(quantity_good) FROM fact_production").fetchone()[0]
d=con.execute("SELECT SUM(good) FROM (SELECT machine_key,SUM(quantity_good) good FROM fact_production GROUP BY machine_key)").fetchone()[0]
assert c==d
(ROOT/"data"/"semantic_metrics_results.json").write_text(json.dumps({"metrics":results,"consistency":{"defect_rate_two_paths_equal":True,"good_output_two_paths_equal":True}},ensure_ascii=False,indent=2,default=str),encoding="utf-8")
con.close()
print("Generated SQL for",len(results),"metrics; two consistency checks passed.")
