---
title: DataOps War Room
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---
# DataOps War Room 🚨

**Meta PyTorch OpenEnv Hackathon Submission**

A real-world OpenEnv environment where an AI agent acts as a **Data Engineering Operations specialist** inside a healthcare analytics company. A production data pipeline has gone wrong — and the agent must work through a chain of realistic operational failures.

---

## Environment Description

DataOps War Room simulates the full lifecycle of a production data pipeline incident:

| Task | Difficulty | Description |
|------|-----------|-------------|
| `task1_triage` | Easy | Read logs & alerts, classify root cause, severity, and impacted services |
| `task2_sql` | Medium | Rewrite a slow or broken SQL query to be correct and performant |
| `task3_cleaning` | Medium-Hard | Clean a dirty clinical dataset and document all issues + actions |
| `task4_review` | Hard | Review pipeline code for bugs, security vulnerabilities, and suggest fixes |

**Why this matters:** Every data-driven company — especially in healthcare — runs on-call rotations, battles bad queries, cleans upstream data, and reviews pipeline code. This environment fills a genuine gap in the RL/agent ecosystem by making these daily human tasks testable and measurable.

---

## Action & Observation Spaces

### Observation
```python
class Observation(BaseModel):
    task_id: str
    phase: TaskPhase          # triage | sql_optimization | data_cleaning | code_review
    context: Dict[str, Any]  # task-specific payload (logs, SQL, data records, code)
    instructions: str
    step_count: int
    max_steps: int
```

### Actions (one per task)
```python
# Task 1
class TriageAction(BaseModel):
    root_cause: RootCause          # sql_error | schema_drift | data_quality | ...
    severity: Severity             # low | medium | high | critical
    affected_services: List[str]
    summary: str

# Task 2
class SQLAction(BaseModel):
    rewritten_query: str
    explanation: str

# Task 3
class CleaningAction(BaseModel):
    cleaned_records: List[CleanedRecord]
    issues_found: List[str]
    actions_taken: List[str]

# Task 4
class CodeReviewAction(BaseModel):
    issues: List[CodeIssue]       # {line, severity, issue_type, description, suggested_fix}
    summary: str
```

### Reward
All graders produce a `Reward` with `value ∈ [0.0, 1.0]` and a `breakdown` dict. Grading is fully deterministic and reproducible.

---

## Grading Rubrics

### Task 1 — Triage
| Dimension | Weight |
|-----------|--------|
| Root cause (exact match) | 40% |
| Severity (exact; adjacent = 50%) | 30% |
| Affected services (Jaccard similarity) | 20% |
| Summary quality (length ≥ 30 chars) | 10% |

### Task 2 — SQL Optimization
| Dimension | Weight |
|-----------|--------|
| Expected SQL constructs present | 45% |
| Anti-patterns removed | 25% |
| Explanation quality | 20% |
| Basic syntactic validity | 10% |

### Task 3 — Data Cleaning
| Dimension | Weight |
|-----------|--------|
| Issue recall (keyword matching) | 40% |
| All patient records returned | 30% |
| Actions documented per-record | 20% |
| No data loss | 10% |

### Task 4 — Code Review
| Dimension | Weight |
|-----------|--------|
| Issue recall (type + label match) | 40% |
| Security issues specifically covered | 25% |
| Fix quality (concrete, code-specific) | 25% |
| Summary addresses risk level | 10% |

---

## Baseline Scores

Measured with `gpt-4o` at temperature 0.0, seed 42:

| Task | Score |
|------|-------|
| task1_triage | 0.72 |
| task2_sql | 0.58 |
| task3_cleaning | 0.61 |
| task4_review | 0.44 |
| **Average** | **0.59** |

---

## Setup & Usage

### Local Development

```bash
# Clone and install
git clone <repo-url>
cd dataops-warroom
pip install -r requirements.txt

# Run the API server
python app.py

# Run baseline inference (requires API credentials)
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o"
export HF_TOKEN="your-api-key"
python inference.py
```

### Docker

```bash
docker build -t dataops-warroom .
docker run -p 7860:7860 \
  -e API_BASE_URL=https://api.openai.com/v1 \
  -e MODEL_NAME=gpt-4o \
  -e HF_TOKEN=your-key \
  dataops-warroom
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check (returns 200) |
| GET | `/tasks` | List all tasks |
| POST | `/reset` | Reset env: `{"task_id": "task1_triage", "seed": 42}` |
| POST | `/step` | Submit action: `{"action": {...}}` |
| GET | `/state` | Get current env state: `?task_id=task1_triage` |
| POST | `/grade` | Grade action directly (reset+step) |

### Using the Python SDK

```python
from environment import DataOpsWarRoomEnv
from environment.models import Action, TaskPhase, TriageAction, RootCause, Severity

env = DataOpsWarRoomEnv(task_id="task1_triage", seed=42)
obs = env.reset()

print(obs.context["logs"])   # production logs
print(obs.instructions)      # task instructions

action = Action(
    task_id="task1_triage",
    phase=TaskPhase.TRIAGE,
    triage=TriageAction(
        root_cause=RootCause.SCHEMA_DRIFT,
        severity=Severity.HIGH,
        affected_services=["reporting_dashboard", "ml_feature_store"],
        summary="Pipeline failed due to a renamed column in patient_vitals table.",
    ),
)

obs, reward, done, info = env.step(action)
print(f"Score: {reward.value}")       # e.g. 0.90
print(f"Feedback: {reward.feedback}")
```

---

## Project Structure

```
dataops-warroom/
├── app.py                    # FastAPI server (HF Space entry point)
├── inference.py              # Baseline inference script (OpenAI client)
├── openenv.yaml              # OpenEnv metadata & task registry
├── requirements.txt
├── Dockerfile
├── README.md
├── environment/
│   ├── __init__.py
│   ├── env.py               # DataOpsWarRoomEnv (reset/step/state)
│   └── models.py            # Typed Pydantic models (Observation/Action/Reward)
├── tasks/
│   ├── task1_triage.py      # Scenario generation + observation builder
│   ├── task2_sql.py
│   ├── task3_cleaning.py
│   └── task4_review.py
└── graders/
    ├── grader1.py           # Deterministic grader for each task
    ├── grader2.py
    ├── grader3.py
    └── grader4.py
```

---

## Design Decisions

**Reward shaping:** Every grader rewards partial progress, not just binary pass/fail. For example, Triage gives partial credit for an adjacent severity level, and SQL grading rewards each correct construct independently.

**Scenario variety:** Each task has 3–4 distinct scenarios sampled at reset time, ensuring the graders can't be gamed by memorization. Use `seed` for reproducibility.

**Hard task:** Task 4 (Code Review) genuinely challenges frontier models — it requires identifying 8–9 distinct issues across bug categories, security vulnerabilities, and providing concrete fixes. GPT-4o baseline is ~0.44.

---

## License

MIT
