from pathlib import Path
import duckdb
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
ROOT=Path(__file__).resolve().parents[1]
con=duckdb.connect(str(ROOT/"data"/"metal_detail.duckdb"),read_only=True)
monthly=con.execute("""SELECT d.year_num,d.month_num,SUM(f.quantity_good) good_units
FROM fact_production f JOIN dim_date d USING(date_key)
GROUP BY 1,2 ORDER BY 1,2""").df()
machine=con.execute("""SELECT m.machine_name,SUM(f.quantity_good) good_units
FROM fact_production f JOIN dim_machine m USING(machine_key)
GROUP BY 1 ORDER BY 2 DESC""").df()
defects=con.execute("""SELECT m.machine_name,100.0*SUM(f.quantity_defect)/SUM(f.quantity_total) defect_pct
FROM fact_production f JOIN dim_machine m USING(machine_key)
GROUP BY 1 ORDER BY 2 DESC""").df()
ops=con.execute("""SELECT o.class_label,o.subclass_label,
SUM(f.machine_minutes) AS total_minutes
FROM fact_production f JOIN dim_operation_taxonomy o USING(operation_key)
GROUP BY 1,2 ORDER BY 3 DESC""").df()
shift=con.execute("""SELECT s.shift_name,SUM(f.quantity_good) good_units
FROM fact_production f JOIN dim_shift s USING(shift_key)
GROUP BY 1 ORDER BY 2 DESC""").df()
con.close()
fig=make_subplots(rows=2,cols=2,subplot_titles=("Придатний випуск за місяцями","Придатний випуск за верстатами","Частка браку за верстатами","Машинний час за класом/підкласом"),specs=[[{"type":"xy"},{"type":"xy"}],[{"type":"xy"},{"type":"xy"}]])
fig.add_trace(go.Scatter(x=monthly.month_num,y=monthly.good_units,mode="lines+markers",name="Придатні деталі"),row=1,col=1)
fig.add_trace(go.Bar(x=machine.machine_name,y=machine.good_units,name="Придатні деталі"),row=1,col=2)
fig.add_trace(go.Bar(x=defects.machine_name,y=defects.defect_pct,name="Брак, %"),row=2,col=1)
fig.add_trace(go.Bar(x=ops.subclass_label,y=ops.total_minutes,name="Машинний час"),row=2,col=2)
fig.update_layout(title="Аналітична панель виробництва «Метал-Деталь»",height=850,barmode="group")
fig.write_html(ROOT/"dashboard"/"index.html",include_plotlyjs="cdn")
(ROOT/"dashboard"/"interpretation.md").write_text("""# Інтерпретація панелі
1. **Випуск за місяцями:** дає змогу бачити сезонні коливання придатного випуску та періоди зниження продуктивності.
2. **Випуск за верстатами:** показує внесок кожного верстата в загальний придатний випуск; значення слід зіставляти з машинним часом.
3. **Частка браку за верстатами:** допомагає визначити обладнання, для якого потрібна додаткова перевірка налаштувань та інструменту.
4. **Машинний час за підкласами операцій:** показує, які технологічні етапи споживають найбільше часу; drill-down можливий від класу до підкласу.
5. **Випуск за змінами** (додаткове бізнес-питання): у SQL-артефакті `10_dice...` та `05_pivot...` порівнюються обсяги за змінами; це допомагає планувати завантаження персоналу.
""",encoding="utf-8")
print("Dashboard written.")
