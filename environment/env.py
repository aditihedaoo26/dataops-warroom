"""
DataOps War Room — Main OpenEnv Environment
Implements: reset() → Observation, step(Action) → (Observation, Reward, bool, StepInfo), state() → EnvState
"""

from __future__ import annotations
import random
from typing import Tuple, Optional

from environment.models import (
    Observation, Action, Reward, StepInfo, EnvState, TaskPhase
)


# ──────────────────────────────────────────
# Lazy imports to avoid circular deps
# ──────────────────────────────────────────

def _load_task(task_id: str):
    if task_id == "task1_triage":
        from tasks.task1_triage import TriageTask
        from graders.grader1 import TriageGrader
        return TriageTask(), TriageGrader()
    elif task_id == "task2_sql":
        from tasks.task2_sql import SQLTask
        from graders.grader2 import SQLGrader
        return SQLTask(), SQLGrader()
    elif task_id == "task3_cleaning":
        from tasks.task3_cleaning import CleaningTask
        from graders.grader3 import CleaningGrader
        return CleaningTask(), CleaningGrader()
    elif task_id == "task4_review":
        from tasks.task4_review import CodeReviewTask
        from graders.grader4 import CodeReviewGrader
        return CodeReviewTask(), CodeReviewGrader()
    else:
        raise ValueError(f"Unknown task_id: {task_id!r}. "
                         f"Valid: task1_triage, task2_sql, task3_cleaning, task4_review")


VALID_TASKS = ["task1_triage", "task2_sql", "task3_cleaning", "task4_review"]


class DataOpsWarRoomEnv:
    """
    OpenEnv-compliant environment for DataOps incident response.

    Usage:
        env = DataOpsWarRoomEnv(task_id="task1_triage", seed=42)
        obs = env.reset()
        action = Action(task_id="task1_triage", phase=TaskPhase.TRIAGE, triage=...)
        obs, reward, done, info = env.step(action)
    """

    def __init__(self, task_id: str = "task1_triage", seed: Optional[int] = None):
        if task_id not in VALID_TASKS:
            raise ValueError(f"task_id must be one of {VALID_TASKS}")
        self.task_id = task_id
        self.seed = seed

        self._step_count: int = 0
        self._max_steps: int = 1
        self._done: bool = False
        self._task = None
        self._grader = None
        self._scenario: Optional[dict] = None
        self._last_obs: Optional[Observation] = None

    # ──────────────────────────────────────
    # Core OpenEnv Interface
    # ──────────────────────────────────────

    def reset(self) -> Observation:
        """Reset environment, sample a new scenario, return initial observation."""
        if self.seed is not None:
            random.seed(self.seed)

        self._step_count = 0
        self._done = False
        self._task, self._grader = _load_task(self.task_id)
        self._scenario = self._task.generate_scenario()
        obs = self._task.get_observation(self._scenario, self._step_count)
        self._last_obs = obs
        return obs

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, StepInfo]:
        """
        Execute one step.
        Returns: (observation, reward, done, info)
        """
        if self._scenario is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        if self._done:
            raise RuntimeError("Episode is finished. Call reset() to start a new one.")
        if action.task_id != self.task_id:
            raise ValueError(f"action.task_id={action.task_id!r} does not match env task {self.task_id!r}")

        self._step_count += 1
        reward: Reward = self._grader.grade(action, self._scenario)
        self._done = True  # single-turn per episode

        obs = self._task.get_observation(self._scenario, self._step_count)
        self._last_obs = obs

        info = StepInfo(
            done=self._done,
            task_id=self.task_id,
            phase=obs.phase,
            step_count=self._step_count,
            metadata={
                "scenario_id": self._scenario.get("id", "unknown"),
                "reward_breakdown": reward.breakdown,
            },
        )
        return obs, reward, self._done, info

    def state(self) -> EnvState:
        """Return the current full state of the environment."""
        phase = self._last_obs.phase if self._last_obs else TaskPhase.TRIAGE
        return EnvState(
            task_id=self.task_id,
            phase=phase,
            step_count=self._step_count,
            max_steps=self._max_steps,
            done=self._done,
            scenario_id=self._scenario.get("id") if self._scenario else None,
            has_active_scenario=self._scenario is not None,
        )

    # ──────────────────────────────────────
    # Convenience
    # ──────────────────────────────────────

    @staticmethod
    def available_tasks() -> list:
        return VALID_TASKS

    def __repr__(self):
        return (f"DataOpsWarRoomEnv(task_id={self.task_id!r}, "
                f"step={self._step_count}, done={self._done})")
