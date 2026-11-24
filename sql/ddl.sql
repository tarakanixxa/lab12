CREATE TABLE IF NOT EXISTS dim_date (
  date_key INTEGER PRIMARY KEY, full_date DATE NOT NULL UNIQUE,
  day_num INTEGER NOT NULL, month_num INTEGER NOT NULL,
  month_name VARCHAR NOT NULL, quarter_num INTEGER NOT NULL, year_num INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_machine (
  machine_key INTEGER PRIMARY KEY, machine_code VARCHAR NOT NULL,
  machine_name VARCHAR NOT NULL, machine_type VARCHAR NOT NULL,
  model VARCHAR NOT NULL, workshop VARCHAR NOT NULL, complex_name VARCHAR NOT NULL,
  valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_product (
  product_key INTEGER PRIMARY KEY, product_code VARCHAR NOT NULL,
  product_name VARCHAR NOT NULL, product_family VARCHAR NOT NULL,
  material VARCHAR NOT NULL, steel_grade VARCHAR NOT NULL,
  valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_operation_taxonomy (
  operation_key INTEGER PRIMARY KEY, class_label VARCHAR NOT NULL,
  class_iri VARCHAR NOT NULL, subclass_label VARCHAR NOT NULL,
  subclass_iri VARCHAR NOT NULL, operation_label VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_shift (
  shift_key INTEGER PRIMARY KEY, shift_name VARCHAR NOT NULL,
  start_hour INTEGER NOT NULL, end_hour INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_production (
  production_id BIGINT PRIMARY KEY, date_key INTEGER NOT NULL,
  machine_key INTEGER NOT NULL, product_key INTEGER NOT NULL,
  operation_key INTEGER NOT NULL, shift_key INTEGER NOT NULL,
  batch_code VARCHAR NOT NULL, quantity_total INTEGER NOT NULL,
  quantity_good INTEGER NOT NULL, quantity_defect INTEGER NOT NULL,
  machine_minutes DOUBLE NOT NULL, material_kg DOUBLE NOT NULL,
  downtime_minutes DOUBLE NOT NULL,
  FOREIGN KEY(date_key) REFERENCES dim_date(date_key),
  FOREIGN KEY(machine_key) REFERENCES dim_machine(machine_key),
  FOREIGN KEY(product_key) REFERENCES dim_product(product_key),
  FOREIGN KEY(operation_key) REFERENCES dim_operation_taxonomy(operation_key),
  FOREIGN KEY(shift_key) REFERENCES dim_shift(shift_key)
);
