"""
Grader 1 — Incident Triage
Deterministic scoring across: root cause, severity, services, summary quality.
"""

from environment.models import Action, Reward


class TriageGrader:
    """
    Scoring breakdown (total = 1.0):
      root_cause   0.40  — exact match on expected root cause
      severity     0.30  — exact match; adjacent severity gets partial credit
      services     0.20  — Jaccard similarity of service sets
      summary      0.10  — non-empty, minimum length
    """

    SEVERITY_ORDER = ["low", "medium", "high", "critical"]

    def grade(self, action: Action, scenario: dict) -> Reward:
        payload = action.triage
        if payload is None:
            return Reward(
                value=0.0,
                breakdown={"root_cause": 0.0, "severity": 0.0, "services": 0.0, "summary": 0.0},
                feedback="No triage action provided.",
            )

        breakdown = {}

        # ── Root cause (0.40) ────────────────────
        expected_rc = scenario["expected_root_cause"]
        actual_rc = payload.root_cause.value
        if actual_rc == expected_rc:
            breakdown["root_cause"] = 0.40
        else:
            breakdown["root_cause"] = 0.0

        # ── Severity (0.30) ──────────────────────
        expected_sev = scenario["expected_severity"]
        actual_sev = payload.severity.value
        if actual_sev == expected_sev:
            breakdown["severity"] = 0.30
        else:
            # Adjacent severity gets partial credit (0.15)
            exp_idx = self.SEVERITY_ORDER.index(expected_sev)
            act_idx = self.SEVERITY_ORDER.index(actual_sev)
            if abs(exp_idx - act_idx) == 1:
                breakdown["severity"] = 0.15
            else:
                breakdown["severity"] = 0.0

        # ── Affected services (0.20) ─────────────
        expected_svcs = set(s.lower() for s in scenario["expected_services"])
        actual_svcs = set(s.lower() for s in (payload.affected_services or []))
        if expected_svcs or actual_svcs:
            intersection = len(expected_svcs & actual_svcs)
            union = len(expected_svcs | actual_svcs)
            jaccard = intersection / union if union > 0 else 0.0
            breakdown["services"] = round(0.20 * jaccard, 4)
        else:
            breakdown["services"] = 0.20

        # ── Summary quality (0.10) ───────────────
        summary = (payload.summary or "").strip()
        if len(summary) >= 30:
            breakdown["summary"] = 0.10
        elif len(summary) >= 10:
            breakdown["summary"] = 0.05
        else:
            breakdown["summary"] = 0.0

        # ── Final score ──────────────────────────
        total = sum(breakdown.values())
        total = round(min(max(total, 0.0), 1.0), 4)

        feedback_parts = []
        if breakdown["root_cause"] == 0:
            feedback_parts.append(f"Root cause incorrect (expected: {expected_rc}, got: {actual_rc}).")
        if breakdown["severity"] < 0.30:
            feedback_parts.append(f"Severity off (expected: {expected_sev}, got: {actual_sev}).")
        if breakdown["services"] < 0.20:
            missed = expected_svcs - actual_svcs
            if missed:
                feedback_parts.append(f"Missed services: {missed}.")
        if not feedback_parts:
            feedback_parts.append("All dimensions correct.")

        return Reward(
            value=total,
            breakdown=breakdown,
            feedback=" ".join(feedback_parts),
        )
