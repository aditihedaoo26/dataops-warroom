"""
DataOps War Room — Local Mock Test
===================================
Run this to verify the full environment works WITHOUT an API key.
Uses hardcoded "perfect agent" responses to test every grader.

Usage:
  python test_mock.py
"""

import sys
sys.path.insert(0, ".")

from environment.env import DataOpsWarRoomEnv
from environment.models import (
    Action, TaskPhase,
    TriageAction, SQLAction, CleaningAction, CleanedRecord,
    CodeReviewAction, CodeIssue,
    RootCause, Severity, IssueType,
)

PASS = "✅"
FAIL = "❌"


def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


def test_task1():
    section("TASK 1 — Incident Triage  (Easy)")
    env = DataOpsWarRoomEnv(task_id="task1_triage", seed=0)
    obs = env.reset()

    print(f"  Scenario: {obs.context['alert'][:80]}...")
    print(f"  Phase:    {obs.phase.value}")

    # Perfect agent response
    action = Action(
        task_id="task1_triage",
        phase=TaskPhase.TRIAGE,
        triage=TriageAction(
            root_cause=RootCause.SCHEMA_DRIFT,
            severity=Severity.HIGH,
            affected_services=["reporting_dashboard", "ml_feature_store"],
            summary="ETL pipeline failed due to a renamed column in patient_vitals table. Downstream reporting and feature store affected.",
        ),
    )

    _, reward, done, info = env.step(action)
    icon = PASS if reward.value >= 0.8 else FAIL
    print(f"\n  Score:     {reward.value:.2f} {icon}")
    print(f"  Breakdown: {reward.breakdown}")
    print(f"  Feedback:  {reward.feedback}")
    assert reward.value >= 0.5, f"Task1 score too low: {reward.value}"
    return reward.value


def test_task2():
    section("TASK 2 — SQL Query Optimization  (Medium)")
    env = DataOpsWarRoomEnv(task_id="task2_sql", seed=0)
    obs = env.reset()

    print(f"  Problem:  {obs.context['problem'][:80]}...")
    print(f"  Phase:    {obs.phase.value}")

    # Perfect agent response with JOIN rewrite
    action = Action(
        task_id="task2_sql",
        phase=TaskPhase.SQL_OPTIMIZATION,
        sql=SQLAction(
            rewritten_query="""\
WITH glucose_stats AS (
    SELECT patient_id,
           AVG(value) AS avg_glucose
    FROM lab_results
    WHERE test_name = 'glucose'
    GROUP BY patient_id
),
diabetes_counts AS (
    SELECT patient_id, COUNT(*) AS diabetes_dx_count
    FROM diagnoses
    WHERE icd_code LIKE 'E11%'
    GROUP BY patient_id
)
SELECT
    p.name,
    gs.avg_glucose,
    COALESCE(dc.diabetes_dx_count, 0) AS diabetes_dx_count
FROM patients p
JOIN glucose_stats gs ON p.id = gs.patient_id
LEFT JOIN diabetes_counts dc ON p.id = dc.patient_id
WHERE gs.avg_glucose > 100
ORDER BY gs.avg_glucose DESC;
""",
            explanation=(
                "The original query had three correlated subqueries that each executed once per patient row, "
                "resulting in O(N) full table scans — approximately 1.5M extra queries for 500k patients. "
                "I rewrote it as two CTEs using GROUP BY + AVG/COUNT pre-aggregation, "
                "then joined results back to patients. This reduces 3 correlated subqueries to a single pass "
                "with indexed GROUP BY, cutting runtime from ~8 minutes to under 10 seconds."
            ),
        ),
    )

    _, reward, done, info = env.step(action)
    icon = PASS if reward.value >= 0.7 else FAIL
    print(f"\n  Score:     {reward.value:.2f} {icon}")
    print(f"  Breakdown: {reward.breakdown}")
    print(f"  Feedback:  {reward.feedback}")
    assert reward.value >= 0.5, f"Task2 score too low: {reward.value}"
    return reward.value


def test_task3():
    section("TASK 3 — Clinical Data Cleaning  (Medium-Hard)")
    env = DataOpsWarRoomEnv(task_id="task3_cleaning", seed=0)
    obs = env.reset()

    print(f"  Table:    {obs.context['table']}")
    print(f"  Records:  {len(obs.context['records'])} dirty records")
    print(f"  Phase:    {obs.phase.value}")

    # Perfect agent response
    records = obs.context["records"]
    cleaned = [
        CleanedRecord(patient_id="PT-1001", fields={"value": 98.5, "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "2024-03-15 09:30:00", "status": "normal"}),
        CleanedRecord(patient_id="PT-1002", fields={"value": "REVIEW_REQUIRED", "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "2024-03-15 10:00:00", "status": "REVIEW_REQUIRED"}),
        CleanedRecord(patient_id="PT-1003", fields={"value": None, "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "2024-03-15 11:15:00", "status": None}),
        CleanedRecord(patient_id="PT-1004", fields={"value": "REVIEW_REQUIRED", "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "2024-03-15 12:00:00", "status": "low"}),
        CleanedRecord(patient_id="PT-1005", fields={"value": 105.3, "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "REVIEW_REQUIRED", "status": "normal"}),
        CleanedRecord(patient_id="PT-1006", fields={"value": "REVIEW_REQUIRED", "unit": "mg/dl", "test_name": "glucose",
                                                     "recorded_at": "2024-03-15 13:30:00", "status": "normal"}),
    ]

    action = Action(
        task_id="task3_cleaning",
        phase=TaskPhase.DATA_CLEANING,
        cleaning=CleaningAction(
            cleaned_records=cleaned,
            issues_found=[
                "PT-1002: implausible glucose value 850.0 (max plausible 600)",
                "PT-1002: wrong status 'normal' for value 850 — should be critical",
                "PT-1003: missing value for glucose test",
                "PT-1003: wrong unit case 'MG/DL' — should be 'mg/dl'",
                "PT-1003: wrong date format '15-03-2024 11:15' — should be YYYY-MM-DD HH:MM:SS",
                "PT-1004: wrong test_name case 'GLUCOSE' — should be 'glucose'",
                "PT-1004: impossible negative glucose value -5.2",
                "PT-1005: future date '2099-03-15' — flagged for review",
                "PT-1006: wrong unit 'mmol/L' (88 mmol/L is implausible for glucose) — flagged",
            ],
            actions_taken=[
                "PT-1001: no changes required — record is valid",
                "PT-1002: flagged value 850.0 as REVIEW_REQUIRED (exceeds plausible max)",
                "PT-1002: flagged status as REVIEW_REQUIRED",
                "PT-1003: corrected unit from 'MG/DL' to 'mg/dl'",
                "PT-1003: converted date from '15-03-2024 11:15' to '2024-03-15 11:15:00'",
                "PT-1004: corrected test_name from 'GLUCOSE' to 'glucose'",
                "PT-1004: flagged negative value -5.2 as REVIEW_REQUIRED",
                "PT-1005: flagged future date '2099-03-15' as REVIEW_REQUIRED",
                "PT-1006: flagged unit mismatch 'mmol/L' → REVIEW_REQUIRED (88 mmol/L implausible)",
            ],
        ),
    )

    _, reward, done, info = env.step(action)
    icon = PASS if reward.value >= 0.6 else FAIL
    print(f"\n  Score:     {reward.value:.2f} {icon}")
    print(f"  Breakdown: {reward.breakdown}")
    print(f"  Feedback:  {reward.feedback}")
    assert reward.value >= 0.4, f"Task3 score too low: {reward.value}"
    return reward.value


def test_task4():
    section("TASK 4 — Pipeline Code Review  (Hard)")
    env = DataOpsWarRoomEnv(task_id="task4_review", seed=0)
    obs = env.reset()

    print(f"  File:     {obs.context['filename']}")
    print(f"  Code:     {len(obs.context['code'])} chars")
    print(f"  Phase:    {obs.phase.value}")

    # Perfect agent response — identifies all issues
    action = Action(
        task_id="task4_review",
        phase=TaskPhase.CODE_REVIEW,
        review=CodeReviewAction(
            issues=[
                CodeIssue(line=9, severity=Severity.CRITICAL, issue_type=IssueType.SECURITY,
                          description="Hardcoded database credential in source code. Anyone with repo access can read the password.",
                          suggested_fix="Use environment variables: DB_PASS = os.environ.get('DB_PASSWORD')"),
                CodeIssue(line=22, severity=Severity.CRITICAL, issue_type=IssueType.SECURITY,
                          description="SQL injection via f-string interpolation. Attacker can manipulate date_str to exfiltrate or destroy data.",
                          suggested_fix="Use parameterized queries: cursor.execute('SELECT * FROM patient_records WHERE admission_date = %s', (date_str,))"),
                CodeIssue(line=27, severity=Severity.HIGH, issue_type=IssueType.BUG,
                          description="Database connection is never closed (resource leak). Under load this will exhaust connection pool.",
                          suggested_fix="Use context manager: with get_connection() as conn: or add conn.close() in finally block"),
                CodeIssue(line=33, severity=Severity.HIGH, issue_type=IssueType.BUG,
                          description="Bare except swallows all exceptions silently. Date parsing failures are hidden, producing corrupt ages.",
                          suggested_fix="except Exception as e: logging.warning(f'Date parse failed: {e}'); df['dob'] = pd.NaT"),
                CodeIssue(line=39, severity=Severity.MEDIUM, issue_type=IssueType.BUG,
                          description="No validation on computed age — negative ages or ages over 150 are allowed due to bad DOB data.",
                          suggested_fix="Add: df = df[(df['age'] >= 0) & (df['age'] <= 130)]"),
                CodeIssue(line=48, severity=Severity.CRITICAL, issue_type=IssueType.SECURITY,
                          description="SQL injection via string concatenation in INSERT. Row values passed directly into SQL string.",
                          suggested_fix="Use parameterized bulk insert with executemany() and placeholders"),
                CodeIssue(line=54, severity=Severity.HIGH, issue_type=IssueType.BUG,
                          description="conn.commit() is never called — all inserts are silently rolled back. Data never persists.",
                          suggested_fix="Add conn.commit() after the insert loop, or use autocommit=True"),
                CodeIssue(line=61, severity=Severity.MEDIUM, issue_type=IssueType.BUG,
                          description="load_to_warehouse() has no error handling. Any failure silently marks pipeline as complete.",
                          suggested_fix="Wrap in try/except and re-raise or log failures with appropriate alerting"),
                CodeIssue(line=66, severity=Severity.HIGH, issue_type=IssueType.BUG,
                          description="CLI input sys.argv[1] used directly without validation — malformed date causes cryptic crash.",
                          suggested_fix="Validate date format: datetime.strptime(sys.argv[1], '%Y-%m-%d')"),
            ],
            summary=(
                "CRITICAL: This code has three SQL injection vulnerabilities and one hardcoded credential "
                "— it should never reach production. The highest priority fix is parameterized queries "
                "and removing the hardcoded password. Secondary critical issue: conn.commit() is missing, "
                "meaning ALL data inserts are silently discarded. Fix security issues first, then the commit bug."
            ),
        ),
    )

    _, reward, done, info = env.step(action)
    icon = PASS if reward.value >= 0.7 else FAIL
    print(f"\n  Score:     {reward.value:.2f} {icon}")
    print(f"  Breakdown: {reward.breakdown}")
    print(f"  Feedback:  {reward.feedback}")
    assert reward.value >= 0.5, f"Task4 score too low: {reward.value}"
    return reward.value


def main():
    print("\n" + "═"*55)
    print("  DataOps War Room — Full Environment Test")
    print("═"*55)

    scores = {}
    try:
        scores["task1_triage"]   = test_task1()
        scores["task2_sql"]      = test_task2()
        scores["task3_cleaning"] = test_task3()
        scores["task4_review"]   = test_task4()
    except Exception as e:
        print(f"\n{FAIL} FAILED: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    avg = sum(scores.values()) / len(scores)

    print("\n" + "═"*55)
    print("  RESULTS SUMMARY")
    print("═"*55)
    for task, score in scores.items():
        icon = PASS if score >= 0.7 else ("⚠️" if score >= 0.5 else FAIL)
        print(f"  {icon} {task:<22} {score:.4f}")
    print(f"\n  {'AVERAGE':<28} {avg:.4f}")
    print("═"*55)
    print(f"\n  {PASS} All tasks passed! Environment is working correctly.\n")


if __name__ == "__main__":
    main()
