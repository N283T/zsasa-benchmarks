-- DuckDB schema for zsasa benchmark evidence.
-- Generated benchmark databases are artifacts under results/ or archives/, not tracked source files.

CREATE TABLE IF NOT EXISTS datasets (
  dataset_id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  role VARCHAR NOT NULL,
  expected_count INTEGER,
  path_or_uri VARCHAR,
  redistribution_status VARCHAR,
  notes VARCHAR
);

CREATE TABLE IF NOT EXISTS tools (
  tool_id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  version VARCHAR,
  commit_sha VARCHAR,
  repository VARCHAR,
  policy VARCHAR,
  notes VARCHAR
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
  run_id VARCHAR PRIMARY KEY,
  benchmark_kind VARCHAR NOT NULL,
  dataset_id VARCHAR NOT NULL,
  tool_id VARCHAR NOT NULL,
  algorithm VARCHAR,
  precision VARCHAR,
  mode VARCHAR,
  n_points INTEGER,
  n_slices INTEGER,
  threads INTEGER,
  source_kind VARCHAR NOT NULL,
  source_path VARCHAR,
  manifest_id VARCHAR,
  created_at TIMESTAMP,
  status VARCHAR NOT NULL DEFAULT 'imported',
  notes VARCHAR,
  FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id),
  FOREIGN KEY (tool_id) REFERENCES tools(tool_id)
);

CREATE TABLE IF NOT EXISTS validation_results (
  run_id VARCHAR NOT NULL,
  structure_id VARCHAR NOT NULL,
  n_atoms INTEGER,
  total_sasa DOUBLE,
  status VARCHAR NOT NULL DEFAULT 'ok',
  notes VARCHAR,
  PRIMARY KEY (run_id, structure_id),
  FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);

CREATE TABLE IF NOT EXISTS performance_results (
  run_id VARCHAR NOT NULL,
  metric VARCHAR NOT NULL,
  value DOUBLE NOT NULL,
  unit VARCHAR,
  statistic VARCHAR,
  n INTEGER,
  notes VARCHAR,
  PRIMARY KEY (run_id, metric, statistic),
  FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  dataset_id VARCHAR,
  kind VARCHAR NOT NULL,
  path VARCHAR NOT NULL,
  sha256 VARCHAR,
  archived_uri VARCHAR,
  notes VARCHAR,
  FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id),
  FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE VIEW IF NOT EXISTS validation_with_runs AS
SELECT
  r.benchmark_kind,
  r.dataset_id,
  r.tool_id,
  r.algorithm,
  r.precision,
  r.mode,
  r.n_points,
  r.n_slices,
  r.threads,
  r.source_kind,
  v.structure_id,
  v.n_atoms,
  v.total_sasa,
  v.status
FROM validation_results AS v
JOIN benchmark_runs AS r USING (run_id);
