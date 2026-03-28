"""
Task 2 — SQL Query Optimization (Medium)
Agent rewrites a broken or slow SQL query to be correct and performant.
"""

import random
from environment.models import Observation, TaskPhase

SCENARIOS = [
    {
        "id": "sql_001",
        "problem_type": "correlated_subquery",
        "schema": """\
CREATE TABLE patients (
    id          INT PRIMARY KEY,
    name        VARCHAR(200),
    dob         DATE,
    gender      CHAR(1),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE lab_results (
    id          INT PRIMARY KEY,
    patient_id  INT REFERENCES patients(id),
    test_name   VARCHAR(100),
    value       FLOAT,
    unit        VARCHAR(20),
    recorded_at TIMESTAMP
);

CREATE TABLE diagnoses (
    id           INT PRIMARY KEY,
    patient_id   INT REFERENCES patients(id),
    icd_code     VARCHAR(20),
    diagnosed_at DATE
);

-- Existing indexes:
CREATE INDEX idx_lab_patient ON lab_results(patient_id);
CREATE INDEX idx_diag_patient ON diagnoses(patient_id);
""",
        "broken_query": """\
-- Find all diabetic patients with average glucose > 100 mg/dL
-- This runs in ~8 minutes on 500k patients — UNACCEPTABLE
SELECT
    p.name,
    (SELECT AVG(lr.value)
     FROM lab_results lr
     WHERE lr.patient_id = p.id
       AND lr.test_name = 'glucose') AS avg_glucose,
    (SELECT COUNT(*)
     FROM diagnoses d
     WHERE d.patient_id = p.id
       AND d.icd_code LIKE 'E11%') AS diabetes_dx_count
FROM patients p
WHERE
    (SELECT AVG(lr.value)
     FROM lab_results lr
     WHERE lr.patient_id = p.id
       AND lr.test_name = 'glucose') > 100
ORDER BY avg_glucose DESC;
""",
        "problem": (
            "Three correlated subqueries execute once per patient row (~500k executions each). "
            "Total runtime: ~8 minutes. Must run under 10 seconds."
        ),
        "expected_keywords": ["JOIN", "GROUP BY", "HAVING", "AVG"],
        "forbidden_patterns": ["SELECT.*SELECT.*FROM.*WHERE.*patient_id = p.id"],
    },
    {
        "id": "sql_002",
        "problem_type": "missing_index_full_scan",
        "schema": """\
CREATE TABLE patient_vitals (
    id             BIGINT PRIMARY KEY,
    patient_id     INT,
    systolic_bp    INT,
    diastolic_bp   INT,
    heart_rate     INT,
    spo2           FLOAT,
    recorded_at    TIMESTAMP,
    ward           VARCHAR(50)
);
-- Table has 200M rows. No index on recorded_at or patient_id.
""",
        "broken_query": """\
-- Fetch today's vitals for reporting dashboard — runs 45s, times out in prod
SELECT *
FROM patient_vitals
WHERE recorded_at >= CURRENT_DATE
ORDER BY patient_id, recorded_at;
""",
        "problem": (
            "Full table scan on 200M row table (no index on recorded_at). "
            "SELECT * fetches all columns including large unneeded fields. "
            "Must run under 2 seconds with proper indexing strategy."
        ),
        "expected_keywords": ["CREATE INDEX", "recorded_at", "patient_id", "systolic_bp", "diastolic_bp"],
        "forbidden_patterns": ["SELECT \\*"],
    },
    {
        "id": "sql_003",
        "problem_type": "n_plus_one_aggregation",
        "schema": """\
CREATE TABLE wards (
    id      INT PRIMARY KEY,
    name    VARCHAR(100),
    floor   INT,
    unit    VARCHAR(50)
);

CREATE TABLE admissions (
    id            INT PRIMARY KEY,
    patient_id    INT,
    ward_id       INT REFERENCES wards(id),
    admitted_at   TIMESTAMP,
    discharged_at TIMESTAMP,
    primary_dx    VARCHAR(20)
);

CREATE TABLE billing_items (
    id           INT PRIMARY KEY,
    admission_id INT REFERENCES admissions(id),
    item_code    VARCHAR(50),
    amount       DECIMAL(10,2),
    billed_at    DATE
);

CREATE INDEX idx_adm_ward ON admissions(ward_id);
CREATE INDEX idx_bill_adm ON billing_items(admission_id);
""",
        "broken_query": """\
-- Monthly ward revenue summary — takes 12 minutes, finance team is waiting
SELECT
    w.name AS ward_name,
    w.unit,
    (SELECT COUNT(DISTINCT a.patient_id)
     FROM admissions a
     WHERE a.ward_id = w.id
       AND a.admitted_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
       AND a.admitted_at <  DATE_TRUNC('month', CURRENT_DATE)) AS patient_count,
    (SELECT SUM(bi.amount)
     FROM billing_items bi
     JOIN admissions a ON bi.admission_id = a.id
     WHERE a.ward_id = w.id
       AND bi.billed_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
       AND bi.billed_at <  DATE_TRUNC('month', CURRENT_DATE)) AS total_revenue,
    (SELECT AVG(
        EXTRACT(EPOCH FROM (a.discharged_at - a.admitted_at)) / 86400
     )
     FROM admissions a
     WHERE a.ward_id = w.id
       AND a.admitted_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
       AND discharged_at IS NOT NULL) AS avg_los_days
FROM wards w
ORDER BY total_revenue DESC NULLS LAST;
""",
        "problem": (
            "Three correlated subqueries per ward. With 80 wards × 3 subqueries = 240 expensive queries. "
            "Must be rewritten as a single pass using CTEs or JOINs + GROUP BY."
        ),
        "expected_keywords": ["WITH", "JOIN", "GROUP BY", "SUM", "AVG", "COUNT"],
        "forbidden_patterns": [],
    },
]


class SQLTask:
    """Task 2: SQL Query Optimization — medium difficulty."""

    def generate_scenario(self) -> dict:
        return random.choice(SCENARIOS)

    def get_observation(self, scenario: dict, step_count: int) -> Observation:
        return Observation(
            task_id="task2_sql",
            phase=TaskPhase.SQL_OPTIMIZATION,
            context={
                "schema": scenario["schema"],
                "broken_query": scenario["broken_query"],
                "problem": scenario["problem"],
                "problem_type": scenario["problem_type"],
            },
            instructions=(
                "You are a senior data engineer at a healthcare analytics company. "
                "The SQL query above is causing production performance issues.\n\n"
                "Your task:\n"
                "  1. rewritten_query — provide a corrected, optimized SQL query "
                "     (include CREATE INDEX statements if needed)\n"
                "  2. explanation — explain exactly what was wrong and what you changed, "
                "     referencing specific lines/patterns from the original\n\n"
                "Constraints:\n"
                "  - The rewritten query must return identical results to the original\n"
                "  - Target: at least 5× improvement in runtime\n"
                "  - Use standard PostgreSQL syntax\n"
                "  - Do not change business logic"
            ),
            step_count=step_count,
            max_steps=1,
        )
