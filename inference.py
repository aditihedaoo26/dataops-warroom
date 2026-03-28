"""
Inference Script — DataOps War Room
=====================================
MANDATORY environment variables:
  API_BASE_URL  — The API endpoint for the LLM (e.g. https://api.openai.com/v1)
  MODEL_NAME    — The model identifier (e.g. gpt-4o, meta-llama/Meta-Llama-3.1-70B-Instruct)
  HF_TOKEN      — Your Hugging Face / API key

Usage:
  python inference.py
  python inference.py --task task1_triage
  python inference.py --seed 42

The script runs all 4 tasks against the environment and prints reproducible baseline scores.
"""

import os
import sys
import json
import argparse
import re
from typing import Optional

from openai import OpenAI

# ── Environment setup ──────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")

if not HF_TOKEN:
    print("WARNING: HF_TOKEN not set. API calls may fail.", file=sys.stderr)

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or "placeholder",
)

# ── Local env import ───────────────────────────────────────────────────────────
from environment.env import DataOpsWarRoomEnv
from environment.models import (
    Action, TaskPhase,
    TriageAction, SQLAction, CleaningAction, CleanedRecord,
    CodeReviewAction, CodeIssue,
    RootCause, Severity, IssueType,
)


# ──────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ──────────────────────────────────────────────────────────────────────────────

def build_prompt(obs) -> str:
    """Build a structured prompt from an Observation."""
    ctx_str = json.dumps(obs.context, indent=2)
    return (
        f"TASK: {obs.task_id}\n"
        f"PHASE: {obs.phase.value}\n\n"
        f"CONTEXT:\n{ctx_str}\n\n"
        f"INSTRUCTIONS:\n{obs.instructions}\n\n"
        f"Respond with a valid JSON object matching the action schema for this phase.\n"
        f"Do not include any text outside the JSON object."
    )


def call_llm(prompt: str, system: str = "") -> str:
    """Call the LLM and return the raw text response."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.0,  # deterministic
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    # Find first { ... }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


# ──────────────────────────────────────────────────────────────────────────────
# Task runners
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert data engineering operations specialist. "
    "You will be given a task context and must respond with a precise JSON object. "
    "Always respond with ONLY valid JSON, no preamble, no explanation outside the JSON."
)


def run_task1(env: DataOpsWarRoomEnv) -> dict:
    obs = env.reset()
    prompt = build_prompt(obs)
    raw = call_llm(prompt, system=SYSTEM_PROMPT)

    try:
        data = extract_json(raw)
        triage = TriageAction(
            root_cause=RootCause(data.get("root_cause", "unknown")),
            severity=Severity(data.get("severity", "low")),
            affected_services=data.get("affected_services", []),
            summary=data.get("summary", ""),
        )
        action = Action(task_id="task1_triage", phase=TaskPhase.TRIAGE, triage=triage)
    except Exception as e:
        print(f"  [task1] Parse error: {e}\n  Raw: {raw[:200]}", file=sys.stderr)
        action = Action(
            task_id="task1_triage", phase=TaskPhase.TRIAGE,
            triage=TriageAction(root_cause=RootCause.UNKNOWN, severity=Severity.LOW,
                                affected_services=[], summary="parse_failed"),
        )

    _, reward, _, info = env.step(action)
    return {"task": "task1_triage", "score": reward.value, "breakdown": reward.breakdown, "feedback": reward.feedback}


def run_task2(env: DataOpsWarRoomEnv) -> dict:
    obs = env.reset()
    prompt = build_prompt(obs)
    raw = call_llm(prompt, system=SYSTEM_PROMPT)

    try:
        data = extract_json(raw)
        sql_action = SQLAction(
            rewritten_query=data.get("rewritten_query", ""),
            explanation=data.get("explanation", ""),
        )
        action = Action(task_id="task2_sql", phase=TaskPhase.SQL_OPTIMIZATION, sql=sql_action)
    except Exception as e:
        print(f"  [task2] Parse error: {e}\n  Raw: {raw[:200]}", file=sys.stderr)
        action = Action(
            task_id="task2_sql", phase=TaskPhase.SQL_OPTIMIZATION,
            sql=SQLAction(rewritten_query="SELECT 1", explanation="parse_failed"),
        )

    _, reward, _, info = env.step(action)
    return {"task": "task2_sql", "score": reward.value, "breakdown": reward.breakdown, "feedback": reward.feedback}


def run_task3(env: DataOpsWarRoomEnv) -> dict:
    obs = env.reset()
    prompt = build_prompt(obs)
    raw = call_llm(prompt, system=SYSTEM_PROMPT)

    try:
        data = extract_json(raw)
        records = [
            CleanedRecord(patient_id=r.get("patient_id", ""), fields=r)
            for r in data.get("cleaned_records", [])
        ]
        cleaning_action = CleaningAction(
            cleaned_records=records,
            issues_found=data.get("issues_found", []),
            actions_taken=data.get("actions_taken", []),
        )
        action = Action(task_id="task3_cleaning", phase=TaskPhase.DATA_CLEANING, cleaning=cleaning_action)
    except Exception as e:
        print(f"  [task3] Parse error: {e}\n  Raw: {raw[:200]}", file=sys.stderr)
        action = Action(
            task_id="task3_cleaning", phase=TaskPhase.DATA_CLEANING,
            cleaning=CleaningAction(cleaned_records=[], issues_found=[], actions_taken=[]),
        )

    _, reward, _, info = env.step(action)
    return {"task": "task3_cleaning", "score": reward.value, "breakdown": reward.breakdown, "feedback": reward.feedback}


def run_task4(env: DataOpsWarRoomEnv) -> dict:
    obs = env.reset()
    prompt = build_prompt(obs)
    raw = call_llm(prompt, system=SYSTEM_PROMPT)

    try:
        data = extract_json(raw)
        issues = [
            CodeIssue(
                line=i.get("line"),
                severity=Severity(i.get("severity", "medium")),
                issue_type=IssueType(i.get("issue_type", "bug")),
                description=i.get("description", ""),
                suggested_fix=i.get("suggested_fix", ""),
            )
            for i in data.get("issues", [])
        ]
        review_action = CodeReviewAction(issues=issues, summary=data.get("summary", ""))
        action = Action(task_id="task4_review", phase=TaskPhase.CODE_REVIEW, review=review_action)
    except Exception as e:
        print(f"  [task4] Parse error: {e}\n  Raw: {raw[:200]}", file=sys.stderr)
        action = Action(
            task_id="task4_review", phase=TaskPhase.CODE_REVIEW,
            review=CodeReviewAction(issues=[], summary="parse_failed"),
        )

    _, reward, _, info = env.step(action)
    return {"task": "task4_review", "score": reward.value, "breakdown": reward.breakdown, "feedback": reward.feedback}


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

TASK_RUNNERS = {
    "task1_triage":   run_task1,
    "task2_sql":      run_task2,
    "task3_cleaning": run_task3,
    "task4_review":   run_task4,
}


def main():
    parser = argparse.ArgumentParser(description="DataOps War Room — Baseline Inference Script")
    parser.add_argument("--task", default=None, help="Run a single task (default: all tasks)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    tasks_to_run = [args.task] if args.task else list(TASK_RUNNERS.keys())

    print(f"\n{'='*60}")
    print(f"  DataOps War Room — Baseline Inference")
    print(f"  Model:  {MODEL_NAME}")
    print(f"  API:    {API_BASE_URL}")
    print(f"  Seed:   {args.seed}")
    print(f"{'='*60}\n")

    results = []
    for task_id in tasks_to_run:
        print(f"Running {task_id}...")
        env = DataOpsWarRoomEnv(task_id=task_id, seed=args.seed)
        runner = TASK_RUNNERS[task_id]
        result = runner(env)
        results.append(result)
        print(f"  Score: {result['score']:.4f}")
        print(f"  Breakdown: {result['breakdown']}")
        print(f"  Feedback: {result['feedback']}\n")

    print(f"{'='*60}")
    avg = sum(r["score"] for r in results) / len(results)
    print(f"  OVERALL AVERAGE SCORE: {avg:.4f}")
    print(f"{'='*60}\n")

    # Write JSON results for CI/automated validators
    with open("baseline_results.json", "w") as f:
        json.dump({"results": results, "average": avg, "model": MODEL_NAME, "seed": args.seed}, f, indent=2)
    print("Results saved to baseline_results.json")


if __name__ == "__main__":
    main()
