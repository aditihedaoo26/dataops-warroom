"""
Task 4 — Pipeline Code Review (Hard)
Agent reviews buggy pipeline code and produces a structured, ranked review.
"""

import random
from environment.models import Observation, TaskPhase

SCENARIOS = [
    {
        "id": "review_001",
        "filename": "pipeline/etl_patient_records.py",
        "code": '''\
import os
import psycopg2
import pandas as pd
import logging
from datetime import datetime

DB_HOST = "db-prod-01"
DB_USER = "admin"
DB_PASS = "P@ssw0rd123!"      # line 9: hardcoded credential
DB_NAME = "healthcare_prod"

def get_connection():
    return psycopg2.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASS, dbname=DB_NAME
    )

def extract_patient_records(date_str: str):
    """Extract all patient records for a given date."""
    conn = get_connection()
    cursor = conn.cursor()

    # line 22: SQL injection vulnerability
    query = f"SELECT * FROM patient_records WHERE admission_date = \'{date_str}\'"
    cursor.execute(query)
    rows = cursor.fetchall()

    # line 27: connection never closed (resource leak)
    return rows

def transform_records(rows):
    """Normalize and validate records."""
    df = pd.DataFrame(rows)

    # line 33: silent failure — exceptions swallowed
    try:
        df[\'dob\'] = pd.to_datetime(df[\'dob\'])
    except:
        pass

    # line 39: no validation — negative ages allowed
    df[\'age\'] = (datetime.now() - df[\'dob\']).dt.days // 365

    return df

def load_to_warehouse(df, table_name):
    """Load transformed data to warehouse."""
    conn = get_connection()

    # line 48: building SQL by string concatenation — injection risk
    for _, row in df.iterrows():
        sql = "INSERT INTO " + table_name + " VALUES (" + \
              ", ".join([str(v) for v in row.values]) + ")"
        conn.cursor().execute(sql)

    # line 54: no commit — data never persisted!
    conn.close()

def run_pipeline(date_str: str):
    logging.info(f"Running pipeline for {date_str}")
    rows = extract_patient_records(date_str)
    df = transform_records(rows)

    # line 61: no error handling around load
    load_to_warehouse(df, "patient_records_clean")
    logging.info("Pipeline complete")

if __name__ == "__main__":
    # line 66: uses sys.argv directly without validation
    import sys
    run_pipeline(sys.argv[1])
''',
        "expected_issues": [
            {"line": 9, "type": "security", "label": "hardcoded_credential"},
            {"line": 22, "type": "security", "label": "sql_injection_fstring"},
            {"line": 27, "type": "bug", "label": "connection_leak"},
            {"line": 33, "type": "bug", "label": "silent_exception"},
            {"line": 39, "type": "bug", "label": "no_age_validation"},
            {"line": 48, "type": "security", "label": "sql_injection_concatenation"},
            {"line": 54, "type": "bug", "label": "missing_commit"},
            {"line": 61, "type": "bug", "label": "no_error_handling"},
            {"line": 66, "type": "bug", "label": "unvalidated_cli_input"},
        ],
    },
    {
        "id": "review_002",
        "filename": "pipeline/data_export.py",
        "code": '''\
import os
import csv
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# line 9: global mutable state — not thread-safe
export_count = 0

API_KEY = "sk-prod-a8f3d2e1b9c4"   # line 12: API key in source code

def fetch_patient_data(patient_id):
    """Fetch patient record from internal API."""
    # line 16: no timeout — hangs forever on slow network
    resp = requests.get(f"http://internal-api/patients/{patient_id}",
                        headers={"Authorization": f"Bearer {API_KEY}"})
    return resp.json()

def export_to_csv(patients, filepath):
    """Export patient list to CSV."""
    global export_count
    export_count += 1

    # line 26: path traversal — attacker controls filepath
    with open(filepath, "w") as f:
        writer = csv.DictWriter(f, fieldnames=patients[0].keys())
        writer.writeheader()
        writer.writerows(patients)

@app.route("/export", methods=["POST"])
def export_endpoint():
    data = request.json

    # line 35: no authentication on this endpoint
    patient_ids = data["patient_ids"]          # line 36: KeyError if missing
    output_path = data["output_path"]          # line 37: path traversal
    patients = [fetch_patient_data(pid) for pid in patient_ids]

    # line 40: no size limit — could export millions of records
    export_to_csv(patients, output_path)

    return jsonify({"status": "ok", "count": len(patients)})

if __name__ == "__main__":
    # line 46: debug=True in production — exposes stack traces
    app.run(host="0.0.0.0", port=5000, debug=True)
''',
        "expected_issues": [
            {"line": 9,  "type": "bug",      "label": "global_mutable_state"},
            {"line": 12, "type": "security", "label": "api_key_in_source"},
            {"line": 16, "type": "bug",      "label": "missing_request_timeout"},
            {"line": 26, "type": "security", "label": "path_traversal"},
            {"line": 35, "type": "security", "label": "unauthenticated_endpoint"},
            {"line": 36, "type": "bug",      "label": "missing_key_check"},
            {"line": 40, "type": "bug",      "label": "no_size_limit"},
            {"line": 46, "type": "security", "label": "debug_mode_production"},
        ],
    },
]


class CodeReviewTask:
    """Task 4: Pipeline Code Review — hard difficulty."""

    def generate_scenario(self) -> dict:
        return random.choice(SCENARIOS)

    def get_observation(self, scenario: dict, step_count: int) -> Observation:
        return Observation(
            task_id="task4_review",
            phase=TaskPhase.CODE_REVIEW,
            context={
                "filename": scenario["filename"],
                "code": scenario["code"],
            },
            instructions=(
                "You are a senior engineer conducting a thorough code review of production pipeline code. "
                "This code caused or is at risk of causing a production incident.\n\n"
                "Your task:\n"
                "  1. issues — list EVERY bug, security vulnerability, and performance problem you find.\n"
                "     For each issue provide:\n"
                "       - line: approximate line number\n"
                "       - severity: critical / high / medium / low\n"
                "       - issue_type: bug | security | performance | style\n"
                "       - description: clear explanation of the problem and its impact\n"
                "       - suggested_fix: concrete code or pattern to fix it\n"
                "  2. summary — overall assessment: how critical is this code? What is the highest-priority fix?\n\n"
                "Be exhaustive. Missing a critical security issue is worse than including a false positive. "
                "Rank issues by severity within your response."
            ),
            step_count=step_count,
            max_steps=1,
        )
