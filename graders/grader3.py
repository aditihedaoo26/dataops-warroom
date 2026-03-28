"""
Grader 3 — Clinical Data Cleaning
Deterministic scoring: issues detected, records returned, actions documented.
"""

from environment.models import Action, Reward


class CleaningGrader:
    """
    Scoring breakdown (total = 1.0):
      issues_detected    0.40  — recall on expected issues found
      records_complete   0.30  — all original patient_ids present in output
      actions_documented 0.20  — actions_taken is specific and per-record
      no_data_loss       0.10  — no records dropped, fields preserved
    """

    def grade(self, action: Action, scenario: dict) -> Reward:
        payload = action.cleaning
        if payload is None:
            return Reward(
                value=0.0,
                breakdown={"issues_detected": 0.0, "records_complete": 0.0,
                           "actions_documented": 0.0, "no_data_loss": 0.0},
                feedback="No cleaning action provided.",
            )

        expected_issues = set(scenario.get("expected_issues", []))
        original_records = scenario.get("records", [])
        original_ids = {r["patient_id"] for r in original_records}

        breakdown = {}

        # ── Issues detected (0.40) ─────────────────
        issues_text = " ".join(
            (i or "").lower() for i in (payload.issues_found or [])
        )
        actions_text = " ".join(
            (a or "").lower() for a in (payload.actions_taken or [])
        )
        combined_text = issues_text + " " + actions_text

        if expected_issues:
            # Check how many expected issue types are mentioned
            hits = 0
            for issue in expected_issues:
                # Normalize: check for key words from the issue label
                keywords = issue.replace("_", " ").split()
                if any(kw in combined_text for kw in keywords):
                    hits += 1
            recall = hits / len(expected_issues)
            breakdown["issues_detected"] = round(0.40 * recall, 4)
        else:
            breakdown["issues_detected"] = 0.40

        # ── Records complete (0.30) ────────────────
        cleaned = payload.cleaned_records or []
        cleaned_ids = {r.patient_id for r in cleaned}
        if original_ids:
            coverage = len(original_ids & cleaned_ids) / len(original_ids)
            breakdown["records_complete"] = round(0.30 * coverage, 4)
        else:
            breakdown["records_complete"] = 0.30

        # ── Actions documented (0.20) ──────────────
        actions = payload.actions_taken or []
        if len(actions) >= 3:
            action_score = 0.10
            # Bonus for per-record specificity (mentions patient IDs)
            pid_mentions = sum(1 for a in actions if any(pid in a for pid in original_ids))
            if pid_mentions >= 2:
                action_score += 0.10
            breakdown["actions_documented"] = round(action_score, 4)
        elif len(actions) >= 1:
            breakdown["actions_documented"] = 0.05
        else:
            breakdown["actions_documented"] = 0.0

        # ── No data loss (0.10) ────────────────────
        # Penalize if cleaned record count < original count
        if len(cleaned) >= len(original_records):
            breakdown["no_data_loss"] = 0.10
        elif len(cleaned) > 0:
            ratio = len(cleaned) / len(original_records)
            breakdown["no_data_loss"] = round(0.10 * ratio, 4)
        else:
            breakdown["no_data_loss"] = 0.0

        total = round(min(max(sum(breakdown.values()), 0.0), 1.0), 4)

        feedback_parts = []
        if breakdown["issues_detected"] < 0.25:
            feedback_parts.append("Many expected issues were not identified.")
        if breakdown["records_complete"] < 0.25:
            feedback_parts.append("Some patient records are missing from the cleaned output.")
        if breakdown["actions_documented"] < 0.10:
            feedback_parts.append("Actions taken are not well documented.")
        if not feedback_parts:
            feedback_parts.append("Good coverage of issues and clean documentation.")

        return Reward(
            value=total,
            breakdown=breakdown,
            feedback=" ".join(feedback_parts),
        )
