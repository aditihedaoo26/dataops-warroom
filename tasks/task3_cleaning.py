"""
Task 3 — Clinical Data Cleaning (Medium-Hard)
Agent cleans a dirty healthcare dataset and documents all issues + actions.
"""

import random
from environment.models import Observation, TaskPhase

SCENARIOS = [
    {
        "id": "clean_001",
        "table": "patient_lab_results",
        "records": [
            {
                "patient_id": "PT-1001",
                "test_name": "glucose",
                "value": "98.5",
                "unit": "mg/dl",
                "recorded_at": "2024-03-15 09:30:00",
                "status": "normal",
            },
            {
                "patient_id": "PT-1002",
                "test_name": "glucose",
                "value": "850.0",   # implausible (fatal level)
                "unit": "mg/dl",
                "recorded_at": "2024-03-15 10:00:00",
                "status": "normal",  # wrong status for value 850
            },
            {
                "patient_id": "PT-1003",
                "test_name": "glucose",
                "value": None,       # missing
                "unit": "MG/DL",    # wrong case
                "recorded_at": "15-03-2024 11:15",  # wrong date format
                "status": None,
            },
            {
                "patient_id": "PT-1004",
                "test_name": "GLUCOSE",  # wrong case
                "value": "-5.2",    # impossible negative glucose
                "unit": "mg/dl",
                "recorded_at": "2024-03-15 12:00:00",
                "status": "low",
            },
            {
                "patient_id": "PT-1005",
                "test_name": "glucose",
                "value": "105.3",
                "unit": "mg/dl",
                "recorded_at": "2099-03-15 08:00:00",  # future date
                "status": "high",
            },
            {
                "patient_id": "PT-1006",
                "test_name": "glucose",
                "value": "88.0",
                "unit": "mmol/L",   # different unit (should be mg/dl; 88 mmol/L is implausible)
                "recorded_at": "2024-03-15 13:30:00",
                "status": "normal",
            },
        ],
        "domain_rules": {
            "glucose": {
                "unit": "mg/dl",
                "min_plausible": 20.0,
                "max_plausible": 600.0,
                "test_name_canonical": "glucose",
                "status_thresholds": {"low": 70, "normal_max": 140, "high": 200},
            }
        },
        "expected_issues": [
            "implausible_value",     # PT-1002: 850
            "wrong_status",          # PT-1002: status normal for 850
            "missing_value",         # PT-1003
            "wrong_unit_case",       # PT-1003
            "wrong_date_format",     # PT-1003
            "wrong_test_name_case",  # PT-1004
            "impossible_negative",   # PT-1004
            "future_date",           # PT-1005
            "wrong_unit",            # PT-1006
        ],
    },
    {
        "id": "clean_002",
        "table": "patient_demographics",
        "records": [
            {
                "patient_id": "PT-2001",
                "name": "  John Smith  ",   # leading/trailing whitespace
                "dob": "1985-06-15",
                "gender": "M",
                "phone": "5551234567",      # missing formatting
                "email": "john.smith@example.com",
                "blood_type": "O+",
            },
            {
                "patient_id": "PT-2002",
                "name": "JANE DOE",         # all caps
                "dob": "06/22/1990",        # wrong format
                "gender": "female",         # not standardized
                "phone": "555-987-6543",
                "email": "jane.doe@",       # invalid email
                "blood_type": "AB-",
            },
            {
                "patient_id": "PT-2003",
                "name": "Bob Johnson",
                "dob": "2045-01-30",        # future DOB (not yet born)
                "gender": "m",              # should be M
                "phone": "000-000-0000",    # invalid phone
                "email": "bob@hospital.org",
                "blood_type": "X+",         # invalid blood type
            },
            {
                "patient_id": "PT-2004",
                "name": "",                 # empty name
                "dob": "1978-11-03",
                "gender": "F",
                "phone": "5559876543",
                "email": "mary@clinic.com",
                "blood_type": "A+",
            },
            {
                "patient_id": "PT-2005",
                "name": "Carlos Rivera",
                "dob": "1965-03-28",
                "gender": "M",
                "phone": "1234",            # too short
                "email": "carlos.rivera@hospital.org",
                "blood_type": "b-",         # wrong case
            },
        ],
        "domain_rules": {
            "gender_canonical": ["M", "F", "O"],
            "blood_types": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
            "dob_format": "YYYY-MM-DD",
            "phone_format": "XXX-XXX-XXXX",
            "max_future_dob": "today",
        },
        "expected_issues": [
            "whitespace_name",
            "wrong_date_format",
            "non_standard_gender",
            "invalid_email",
            "future_dob",
            "invalid_phone",
            "invalid_blood_type",
            "empty_name",
            "short_phone",
            "wrong_blood_type_case",
        ],
    },
]


class CleaningTask:
    """Task 3: Clinical Data Cleaning — medium-hard difficulty."""

    def generate_scenario(self) -> dict:
        return random.choice(SCENARIOS)

    def get_observation(self, scenario: dict, step_count: int) -> Observation:
        return Observation(
            task_id="task3_cleaning",
            phase=TaskPhase.DATA_CLEANING,
            context={
                "table": scenario["table"],
                "records": scenario["records"],
                "domain_rules": scenario["domain_rules"],
            },
            instructions=(
                "You are a clinical data engineer. The upstream dataset above contains quality issues "
                "that will corrupt downstream pipelines and reporting.\n\n"
                "Your task:\n"
                "  1. cleaned_records — return the full list of records with all issues fixed. "
                "     Each record must have the same patient_id as the original.\n"
                "  2. issues_found — list every data quality issue you detected "
                "     (be specific: include patient_id and field name for each issue)\n"
                "  3. actions_taken — list every cleaning action you performed "
                "     (e.g. 'PT-1003: converted date format from DD-MM-YYYY to YYYY-MM-DD')\n\n"
                "Rules:\n"
                "  - Use domain rules provided for valid ranges, formats, and enumerations\n"
                "  - For implausible/impossible values you cannot fix, flag as REVIEW_REQUIRED\n"
                "  - Do not drop records — return all of them\n"
                "  - Document every change, even cosmetic ones"
            ),
            step_count=step_count,
            max_steps=1,
        )
