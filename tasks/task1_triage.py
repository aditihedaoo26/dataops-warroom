"""
Task 1 — Incident Triage (Easy)
Agent reads production logs + alert, classifies root cause, severity, services.
"""

import random
from environment.models import Observation, TaskPhase

SCENARIOS = [
    {
        "id": "triage_001",
        "logs": """\
2024-03-15 02:13:41 INFO  pipeline.orchestrator  - Starting nightly ETL run
2024-03-15 02:13:44 INFO  pipeline.etl           - Connecting to warehouse db-prod-01
2024-03-15 02:13:45 ERROR pipeline.etl           - Failed to execute query on patient_vitals
2024-03-15 02:13:45 ERROR sqlalchemy              - ProgrammingError: column "blood_presure" does not exist
                                                    LINE 1: SELECT patient_id, blood_presure, heart_rate FROM patient_vitals
2024-03-15 02:13:45 ERROR pipeline.etl           - Original query: SELECT patient_id, blood_presure, heart_rate FROM patient_vitals WHERE date = '2024-03-15'
2024-03-15 02:13:46 ERROR pipeline.orchestrator  - Task etl_patient_vitals FAILED after 1 retries
2024-03-15 02:13:46 INFO  pipeline.alerting      - Firing: NIGHTLY_PIPELINE_FAILURE severity=HIGH
""",
        "alert": (
            "🔴 ALERT [HIGH]: Nightly ETL pipeline failed at 02:13 UTC. "
            "Stage: etl_patient_vitals. DB: db-prod-01. "
            "Downstream services at risk: reporting_dashboard, ml_feature_store. "
            "On-call engineer: YOU."
        ),
        "expected_root_cause": "schema_drift",
        "expected_severity": "high",
        "expected_services": ["reporting_dashboard", "ml_feature_store"],
    },
    {
        "id": "triage_002",
        "logs": """\
2024-03-16 03:44:58 INFO  pipeline.etl           - Starting lab_results extraction (est. rows: 48M)
2024-03-16 03:45:28 ERROR pipeline.etl           - OperationalError: canceling statement due to statement timeout
2024-03-16 03:45:28 ERROR pipeline.etl           - Query exceeded 30s limit on table lab_results
2024-03-16 03:45:29 WARN  pipeline.etl           - Retry 1/3 ...
2024-03-16 03:46:01 ERROR pipeline.etl           - Retry timed out again. Giving up.
2024-03-16 03:46:02 ERROR pipeline.orchestrator  - Task etl_lab_results FAILED (3 retries exhausted)
2024-03-16 03:46:02 INFO  pipeline.alerting      - Firing: PIPELINE_TIMEOUT severity=MEDIUM
""",
        "alert": (
            "🟡 ALERT [MEDIUM]: Pipeline timeout at 03:45 UTC. "
            "lab_results extraction exceeded 30s statement timeout (3 retries). "
            "Affected services: lab_analytics_portal. "
            "Note: table size grew from 32M → 48M rows this week."
        ),
        "expected_root_cause": "timeout",
        "expected_severity": "medium",
        "expected_services": ["lab_analytics_portal"],
    },
    {
        "id": "triage_003",
        "logs": """\
2024-03-17 01:00:03 INFO  pipeline.etl           - Starting daily patient_records load
2024-03-17 01:00:07 ERROR pipeline.validation    - DQ CHECK FAILED: 'diagnosis_code' null rate = 34.2% (threshold 5%)
2024-03-17 01:00:07 ERROR pipeline.validation    - DQ CHECK FAILED: 'admission_date' invalid formats = 11.8% (threshold 2%)
2024-03-17 01:00:07 ERROR pipeline.validation    - DQ CHECK FAILED: 'patient_dob' future dates detected (count=412)
2024-03-17 01:00:08 ERROR pipeline.orchestrator  - Task validate_patient_records FAILED — data quality thresholds exceeded
2024-03-17 01:00:08 INFO  pipeline.alerting      - Firing: DATA_QUALITY_FAILURE severity=CRITICAL
""",
        "alert": (
            "🔴 ALERT [CRITICAL]: Data quality failure at 01:00 UTC. "
            "Patient records from upstream vendor have severe quality issues (nulls, bad formats, future DOBs). "
            "Downstream impact: billing_system (revenue), compliance_reports (regulatory). "
            "Patient count affected: ~14,000 records."
        ),
        "expected_root_cause": "data_quality",
        "expected_severity": "critical",
        "expected_services": ["billing_system", "compliance_reports"],
    },
    {
        "id": "triage_004",
        "logs": """\
2024-03-18 04:22:11 INFO  pipeline.etl           - Connecting to source DB replica-02
2024-03-18 04:22:12 ERROR pipeline.etl           - psycopg2.OperationalError: FATAL: password authentication failed for user "etl_svc"
2024-03-18 04:22:12 ERROR pipeline.etl           - Could not connect to replica-02
2024-03-18 04:22:13 ERROR pipeline.orchestrator  - Task extract_prescriptions FAILED — cannot connect to source
2024-03-18 04:22:13 INFO  pipeline.alerting      - Firing: PIPELINE_AUTH_ERROR severity=HIGH
""",
        "alert": (
            "🔴 ALERT [HIGH]: Authentication failure at 04:22 UTC. "
            "ETL service account credentials rejected by replica-02. "
            "Possible cause: scheduled credential rotation ran at 04:00. "
            "Affected: prescriptions_dashboard, pharmacy_reports."
        ),
        "expected_root_cause": "permission",
        "expected_severity": "high",
        "expected_services": ["prescriptions_dashboard", "pharmacy_reports"],
    },
]


class TriageTask:
    """Task 1: Incident Triage — easy difficulty."""

    def generate_scenario(self) -> dict:
        return random.choice(SCENARIOS)

    def get_observation(self, scenario: dict, step_count: int) -> Observation:
        return Observation(
            task_id="task1_triage",
            phase=TaskPhase.TRIAGE,
            context={
                "logs": scenario["logs"],
                "alert": scenario["alert"],
            },
            instructions=(
                "You are the on-call SRE at a healthcare analytics company. "
                "A production pipeline has just failed. Analyze the logs and alert above.\n\n"
                "You must provide:\n"
                "  1. root_cause — one of: sql_error, schema_drift, data_quality, network, permission, timeout, unknown\n"
                "  2. severity — one of: low, medium, high, critical\n"
                "  3. affected_services — list of downstream services impacted\n"
                "  4. summary — a concise incident summary for the engineering team (2–4 sentences)\n\n"
                "Be precise. Avoid guessing — base your assessment only on the log evidence."
            ),
            step_count=step_count,
            max_steps=1,
        )
