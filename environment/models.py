"""
DataOps War Room — Typed Pydantic Models
Implements OpenEnv spec: Observation, Action, Reward
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


# ──────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────

class TaskPhase(str, Enum):
    TRIAGE = "triage"
    SQL_OPTIMIZATION = "sql_optimization"
    DATA_CLEANING = "data_cleaning"
    CODE_REVIEW = "code_review"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RootCause(str, Enum):
    SQL_ERROR = "sql_error"
    SCHEMA_DRIFT = "schema_drift"
    DATA_QUALITY = "data_quality"
    NETWORK = "network"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class IssueType(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"


# ──────────────────────────────────────────
# Observation
# ──────────────────────────────────────────

class Observation(BaseModel):
    """What the agent sees at each step."""
    task_id: str = Field(..., description="Unique task identifier")
    phase: TaskPhase = Field(..., description="Current task phase")
    context: Dict[str, Any] = Field(..., description="Task-specific payload (logs, queries, data, code)")
    instructions: str = Field(..., description="Natural language instructions for the agent")
    step_count: int = Field(default=0, ge=0)
    max_steps: int = Field(default=1, ge=1)


# ──────────────────────────────────────────
# Actions (one per task type)
# ──────────────────────────────────────────

class TriageAction(BaseModel):
    """Agent's response for Task 1: Incident Triage."""
    root_cause: RootCause = Field(..., description="Classified root cause of the failure")
    severity: Severity = Field(..., description="Assessed severity level")
    affected_services: List[str] = Field(default_factory=list, description="List of impacted downstream services")
    summary: str = Field(..., min_length=10, description="Human-readable incident summary")


class SQLAction(BaseModel):
    """Agent's response for Task 2: SQL Optimization."""
    rewritten_query: str = Field(..., min_length=10, description="The optimized SQL query")
    explanation: str = Field(..., min_length=20, description="Explanation of changes made and why")


class CleanedRecord(BaseModel):
    """A single cleaned data record."""
    patient_id: str
    fields: Dict[str, Any] = Field(default_factory=dict)


class CleaningAction(BaseModel):
    """Agent's response for Task 3: Clinical Data Cleaning."""
    cleaned_records: List[CleanedRecord] = Field(default_factory=list)
    issues_found: List[str] = Field(default_factory=list, description="List of data quality issues identified")
    actions_taken: List[str] = Field(default_factory=list, description="List of cleaning actions performed")


class CodeIssue(BaseModel):
    """A single identified code issue."""
    line: Optional[int] = Field(None, description="Line number where issue occurs")
    severity: Severity
    issue_type: IssueType
    description: str = Field(..., min_length=10)
    suggested_fix: str = Field(..., min_length=10)


class CodeReviewAction(BaseModel):
    """Agent's response for Task 4: Code Review."""
    issues: List[CodeIssue] = Field(default_factory=list)
    summary: str = Field(..., min_length=20, description="Overall assessment of the code")


class Action(BaseModel):
    """Top-level action container — fill exactly the field matching the current phase."""
    task_id: str
    phase: TaskPhase
    triage: Optional[TriageAction] = None
    sql: Optional[SQLAction] = None
    cleaning: Optional[CleaningAction] = None
    review: Optional[CodeReviewAction] = None

    def get_payload(self):
        if self.phase == TaskPhase.TRIAGE:
            return self.triage
        elif self.phase == TaskPhase.SQL_OPTIMIZATION:
            return self.sql
        elif self.phase == TaskPhase.DATA_CLEANING:
            return self.cleaning
        elif self.phase == TaskPhase.CODE_REVIEW:
            return self.review
        return None


# ──────────────────────────────────────────
# Reward
# ──────────────────────────────────────────

class Reward(BaseModel):
    """Graded reward for an agent action."""
    value: float = Field(..., ge=0.0, le=1.0, description="Overall reward in [0, 1]")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Per-dimension scores")
    feedback: str = Field(default="", description="Human-readable grader feedback")


# ──────────────────────────────────────────
# Info
# ──────────────────────────────────────────

class StepInfo(BaseModel):
    """Metadata returned alongside every step."""
    done: bool
    task_id: str
    phase: TaskPhase
    step_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ──────────────────────────────────────────
# State
# ──────────────────────────────────────────

class EnvState(BaseModel):
    """Full environment state (returned by state())."""
    task_id: str
    phase: TaskPhase
    step_count: int
    max_steps: int
    done: bool
    scenario_id: Optional[str] = None
    has_active_scenario: bool = False
