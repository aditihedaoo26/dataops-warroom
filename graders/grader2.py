"""
Grader 2 — SQL Query Optimization
Deterministic scoring: keyword presence, forbidden pattern removal, explanation quality.
"""

import re
from environment.models import Action, Reward


class SQLGrader:
    """
    Scoring breakdown (total = 1.0):
      keywords_present   0.45  — expected SQL keywords/constructs in rewritten query
      no_forbidden       0.25  — forbidden anti-patterns removed
      explanation        0.20  — explanation references specific changes
      basic_validity     0.10  — query is non-empty and syntactically plausible
    """

    def grade(self, action: Action, scenario: dict) -> Reward:
        payload = action.sql
        if payload is None:
            return Reward(
                value=0.0,
                breakdown={"keywords_present": 0.0, "no_forbidden": 0.0,
                           "explanation": 0.0, "basic_validity": 0.0},
                feedback="No SQL action provided.",
            )

        query = (payload.rewritten_query or "").upper()
        explanation = (payload.explanation or "").lower()
        breakdown = {}

        # ── Expected keywords (0.45) ──────────────
        expected_kws = [kw.upper() for kw in scenario.get("expected_keywords", [])]
        if expected_kws:
            hits = sum(1 for kw in expected_kws if kw in query)
            breakdown["keywords_present"] = round(0.45 * (hits / len(expected_kws)), 4)
        else:
            breakdown["keywords_present"] = 0.45

        # ── Forbidden patterns removed (0.25) ─────
        forbidden = scenario.get("forbidden_patterns", [])
        if forbidden:
            violations = sum(
                1 for pat in forbidden
                if re.search(pat, payload.rewritten_query or "", re.IGNORECASE | re.DOTALL)
            )
            if violations == 0:
                breakdown["no_forbidden"] = 0.25
            else:
                breakdown["no_forbidden"] = round(0.25 * (1 - violations / len(forbidden)), 4)
        else:
            breakdown["no_forbidden"] = 0.25

        # ── Explanation quality (0.20) ─────────────
        explanation_score = 0.0
        if len(explanation) >= 50:
            explanation_score += 0.10
        # References original problem
        problem_words = set(scenario.get("problem", "").lower().split())
        explanation_words = set(explanation.split())
        overlap = len(problem_words & explanation_words) / max(len(problem_words), 1)
        if overlap > 0.15:
            explanation_score += 0.10
        breakdown["explanation"] = round(min(explanation_score, 0.20), 4)

        # ── Basic validity (0.10) ─────────────────
        q = (payload.rewritten_query or "").strip()
        has_select = bool(re.search(r"\bSELECT\b|\bCREATE\b|\bWITH\b", q, re.IGNORECASE))
        has_from = bool(re.search(r"\bFROM\b|\bINDEX\b", q, re.IGNORECASE))
        breakdown["basic_validity"] = 0.10 if (has_select and has_from and len(q) > 20) else 0.0

        total = round(min(max(sum(breakdown.values()), 0.0), 1.0), 4)

        missed_kws = [kw for kw in expected_kws if kw not in query]
        feedback = ""
        if missed_kws:
            feedback += f"Missing expected constructs: {missed_kws}. "
        if breakdown["no_forbidden"] < 0.25:
            feedback += "Anti-pattern still present in rewritten query. "
        if breakdown["explanation"] < 0.10:
            feedback += "Explanation too brief or doesn't reference the original problem. "
        if not feedback:
            feedback = "Well-optimized query with clear explanation."

        return Reward(value=total, breakdown=breakdown, feedback=feedback.strip())
