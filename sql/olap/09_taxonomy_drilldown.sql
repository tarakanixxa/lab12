SELECT o.class_label,o.subclass_label,o.operation_label,SUM(f.machine_minutes) machine_minutes FROM fact_production f JOIN dim_operation_taxonomy o USING(operation_key) GROUP BY 1,2,3 ORDER BY 1,2,3;
