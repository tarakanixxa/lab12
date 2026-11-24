SELECT p.product_name,SUM(f.quantity_total) produced FROM fact_production f JOIN dim_date d USING(date_key) JOIN dim_product p USING(product_key) WHERE d.year_num=2025 GROUP BY p.product_name;
