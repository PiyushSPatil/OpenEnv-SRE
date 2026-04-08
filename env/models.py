from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal


# -----------------------------
# Observation Model
# -----------------------------
class Observation(BaseModel):
    """
    Represents the current state of the environment.
    This is what the agent sees at each step.
    """

    logs: List[str] = Field(
        ..., description="Recent system logs including errors, warnings, and info messages"
    )

    metrics: Dict[str, float] = Field(
        ..., description="System performance metrics like CPU, memory, latency"
    )

    alerts: List[str] = Field(
        ..., description="Active alerts triggered by monitoring systems"
    )

    system_status: Literal["healthy", "degraded", "down"] = Field(
        ..., description="Overall system health status"
    )

    step_count: int = Field(
        ..., description="Current step number in the episode"
    )

    max_steps: int = Field(
        ..., description="Maximum allowed steps before termination"
    )

    task_id: str = Field(
        ..., description="Identifier for the current task"
    )

    description: Optional[str] = Field(
        None, description="Optional natural language description of the current situation"
    )


# -----------------------------
# Action Model
# -----------------------------
class Action(BaseModel):
    """
    Action taken by the agent to modify the environment.
    """

    action_type: Literal[
        "restart_service",
        "scale_service",
        "clear_cache",
        "fix_db_connection",
        "noop"
    ] = Field(..., description="Type of action to perform")

    target: Optional[str] = Field(
        None,
        description="Target component (e.g., 'backend', 'database', 'cache')"
    )


# -----------------------------
# Reward Model
# -----------------------------
class Reward(BaseModel):
    """
    Reward returned after each action.
    """

    value: float = Field(
        ..., description="Numerical reward signal (-1.0 to +1.0)"
    )

    reason: Optional[str] = Field(
        None,
        description="Explanation for the reward (useful for debugging and analysis)"
    )


# -----------------------------
# Step Result Model
# -----------------------------
class StepResult(BaseModel):
    """
    Full response returned from step()
    """

    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Additional debug or metadata info"
    )


# -----------------------------
# Internal State Model
# -----------------------------
class InternalState(BaseModel):
    """
    Hidden internal state of the environment.
    Not fully exposed to the agent.
    """

    # System flags
    db_connected: bool
    cache_clean: bool
    services_running: Dict[str, bool]

    # Metrics
    cpu_usage: float
    latency: float

    # Progress tracking
    issue_identified: bool
    issue_fixed: bool

    # Step tracking
    step_count: int
    max_steps: int

    # Task metadata
    task_id: str