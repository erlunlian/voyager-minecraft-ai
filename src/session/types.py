"""Type definitions for session management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Import shared types
from models import BotState, ExecutionResult, InventoryItem, Position


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(Enum):
    """Status of a session."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass
class Task:
    """Represents a task in the session."""

    task_id: int
    session_id: int
    description: str
    status: TaskStatus
    created_at: str
    completed_at: Optional[str] = None
    success: Optional[bool] = None
    evaluation: Optional[Dict[str, Any]] = None  # Keep as dict for DB serialization
    bot_state_before: Optional[BotState] = None
    bot_state_after: Optional[BotState] = None
    generated_code: Optional[str] = None
    execution_result: Optional[ExecutionResult] = None


@dataclass
class Session:
    """Represents a bot session."""

    session_id: int
    bot_username: str
    server_host: str
    start_time: str
    last_update: str
    status: SessionStatus
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionStats:
    """Statistics for a session."""

    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    skills_learned: int
    average_success_rate: float = 0.0

    def __post_init__(self):
        """Calculate derived fields."""
        if self.total_tasks > 0:
            self.average_success_rate = self.successful_tasks / self.total_tasks


@dataclass
class LearnedSkill:
    """Represents a skill learned during a session."""

    skill_id: int
    session_id: int
    task_id: int
    skill_name: str
    skill_code: str
    created_at: str


@dataclass
class BotStateSnapshot:
    """Snapshot of bot state at a point in time."""

    state_id: int
    session_id: int
    timestamp: str
    position: Position
    inventory: List[InventoryItem]
    health: float
    food: float
    event_type: str
