"""
DataOps War Room — FastAPI App
Serves the OpenEnv HTTP interface for Hugging Face Spaces.

Endpoints:
  GET  /          → health check (returns 200)
  POST /reset     → reset(task_id, seed) → Observation
  POST /step      → step(Action) → {observation, reward, done, info}
  GET  /state     → state() → EnvState
  GET  /tasks     → list available tasks
  POST /grade     → grade a single action directly (for testing)
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from environment.env import DataOpsWarRoomEnv
from environment.models import Action, Observation, Reward, StepInfo, EnvState

app = FastAPI(
    title="DataOps War Room",
    description="OpenEnv environment for real-world DataOps incident response.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store (single-session; for multi-user extend with session IDs) ──
_envs: dict[str, DataOpsWarRoomEnv] = {}


def _get_env(task_id: str) -> DataOpsWarRoomEnv:
    if task_id not in _envs:
        _envs[task_id] = DataOpsWarRoomEnv(task_id=task_id)
    return _envs[task_id]


# ── Request/Response schemas ──────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "task1_triage"
    seed: Optional[int] = None


class ResetResponse(BaseModel):
    observation: Observation


class StepRequest(BaseModel):
    action: Action


class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: StepInfo


class TaskInfo(BaseModel):
    id: str
    name: str
    difficulty: str
    description: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def health():
    """Returns 200 if the server is up. Used by automated validators."""
    return {"status": "ok", "environment": "dataops-warroom", "version": "1.0.0"}


@app.post("/reset", response_model=ResetResponse, summary="Reset environment")
def reset(req: ResetRequest):
    """
    Reset the environment for a given task_id. Returns the initial observation.
    Call this before every new episode.
    """
    try:
        env = DataOpsWarRoomEnv(task_id=req.task_id, seed=req.seed)
        _envs[req.task_id] = env
        obs = env.reset()
        return ResetResponse(observation=obs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse, summary="Step the environment")
def step(req: StepRequest):
    """
    Execute one agent action. Returns observation, reward, done flag, and info.
    You must call /reset first.
    """
    task_id = req.action.task_id
    env = _envs.get(task_id)
    if env is None or env._scenario is None:
        raise HTTPException(
            status_code=400,
            detail=f"No active episode for task '{task_id}'. Call /reset first.",
        )
    try:
        obs, reward, done, info = env.step(req.action)
        return StepResponse(observation=obs, reward=reward, done=done, info=info)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/state", response_model=EnvState, summary="Get environment state")
def state(task_id: str = "task1_triage"):
    """Return the current state of the environment for a given task."""
    env = _envs.get(task_id)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail=f"No environment initialized for task '{task_id}'. Call /reset first.",
        )
    return env.state()


@app.get("/tasks", summary="List available tasks")
def list_tasks():
    """List all available tasks with metadata."""
    tasks = [
        TaskInfo(id="task1_triage",   name="Incident Triage",        difficulty="easy",        description="Classify root cause and severity from production logs."),
        TaskInfo(id="task2_sql",      name="SQL Query Optimization",  difficulty="medium",      description="Rewrite a slow or broken SQL query to be performant."),
        TaskInfo(id="task3_cleaning", name="Clinical Data Cleaning",  difficulty="medium_hard", description="Clean dirty healthcare records and document all issues."),
        TaskInfo(id="task4_review",   name="Pipeline Code Review",    difficulty="hard",        description="Find all bugs and security issues in pipeline code."),
    ]
    return {"tasks": [t.dict() for t in tasks]}


@app.post("/grade", summary="Grade an action directly (for testing)")
def grade_action(req: StepRequest):
    """
    Convenience endpoint: reset + step in one call.
    Useful for the inference script to get reproducible scores.
    """
    task_id = req.action.task_id
    env = DataOpsWarRoomEnv(task_id=task_id, seed=42)
    _envs[task_id] = env
    env.reset()
    try:
        obs, reward, done, info = env.step(req.action)
        return {
            "reward": reward.dict(),
            "done": done,
            "info": info.dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
