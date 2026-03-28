"""
Grader 4 — Pipeline Code Review
Deterministic scoring: issue recall, security coverage, fix quality, summary.
"""

from environment.models import Action, Reward, IssueType


class CodeReviewGrader:
    """
    Scoring breakdown (total = 1.0):
      issue_recall       0.40  — % of expected issues found (by type + approximate line)
      security_coverage  0.25  — all security issues specifically identified
      fix_quality        0.25  — each found issue has a concrete, non-trivial fix
      summary_quality    0.10  — summary addresses overall risk level
    """

    def grade(self, action: Action, scenario: dict) -> Reward:
        payload = action.review
        if payload is None:
            return Reward(
                value=0.0,
                breakdown={"issue_recall": 0.0, "security_coverage": 0.0,
                           "fix_quality": 0.0, "summary_quality": 0.0},
                feedback="No code review action provided.",
            )

        expected_issues = scenario.get("expected_issues", [])
        found_issues = payload.issues or []
        breakdown = {}

        # Build searchable text from found issues
        found_texts = []
        for issue in found_issues:
            text = (
                f"{issue.description.lower()} "
                f"{issue.suggested_fix.lower()} "
                f"{issue.issue_type.value.lower()}"
            )
            found_texts.append((issue, text))

        # ── Issue recall (0.40) ────────────────────
        if expected_issues:
            hits = 0
            for exp in expected_issues:
                label_words = exp["label"].replace("_", " ").split()
                issue_type = exp["type"]
                # Check if any found issue mentions key words + correct type
                for issue, text in found_texts:
                    type_match = issue.issue_type.value == issue_type
                    keyword_match = any(w in text for w in label_words)
                    if type_match and keyword_match:
                        hits += 1
                        break
                    # Partial: keyword match without type match
                    elif keyword_match:
                        hits += 0.5
                        break
            recall = min(hits / len(expected_issues), 1.0)
            breakdown["issue_recall"] = round(0.40 * recall, 4)
        else:
            breakdown["issue_recall"] = 0.0

        # ── Security coverage (0.25) ───────────────
        expected_security = [e for e in expected_issues if e["type"] == "security"]
        if expected_security:
            sec_hits = 0
            for exp in expected_security:
                label_words = exp["label"].replace("_", " ").split()
                for issue, text in found_texts:
                    if issue.issue_type == IssueType.SECURITY and any(w in text for w in label_words):
                        sec_hits += 1
                        break
            sec_recall = sec_hits / len(expected_security)
            breakdown["security_coverage"] = round(0.25 * sec_recall, 4)
        else:
            breakdown["security_coverage"] = 0.25

        # ── Fix quality (0.25) ─────────────────────
        if found_issues:
            quality_scores = []
            for issue in found_issues:
                fix = (issue.suggested_fix or "").strip()
                score = 0.0
                if len(fix) >= 20:
                    score += 0.5
                # Contains code-like content
                code_indicators = ["=", "(", ")", "import", "use", "replace", "env", "param", "close"]
                if any(ind in fix.lower() for ind in code_indicators):
                    score += 0.5
                quality_scores.append(score)
            avg_quality = sum(quality_scores) / len(quality_scores)
            breakdown["fix_quality"] = round(0.25 * avg_quality, 4)
        else:
            breakdown["fix_quality"] = 0.0

        # ── Summary quality (0.10) ─────────────────
        summary = (payload.summary or "").lower()
        risk_words = ["critical", "high", "security", "vulnerability", "urgent", "risk", "dangerous"]
        if len(summary) >= 30 and any(w in summary for w in risk_words):
            breakdown["summary_quality"] = 0.10
        elif len(summary) >= 15:
            breakdown["summary_quality"] = 0.05
        else:
            breakdown["summary_quality"] = 0.0

        total = round(min(max(sum(breakdown.values()), 0.0), 1.0), 4)

        # Feedback
        feedback_parts = []
        n_expected_sec = len([e for e in expected_issues if e["type"] == "security"])
        n_found_sec = sum(1 for i in found_issues if i.issue_type == IssueType.SECURITY)
        if breakdown["issue_recall"] < 0.25:
            feedback_parts.append(f"Only caught {breakdown['issue_recall']/0.40*100:.0f}% of expected issues.")
        if n_found_sec < n_expected_sec:
            feedback_parts.append(f"Missed {n_expected_sec - n_found_sec} security issue(s).")
        if breakdown["fix_quality"] < 0.15:
            feedback_parts.append("Suggested fixes lack specificity — include concrete code.")
        if not feedback_parts:
            feedback_parts.append("Thorough review with good coverage and concrete fixes.")

        return Reward(
            value=total,
            breakdown=breakdown,
            feedback=" ".join(feedback_parts),
        )
