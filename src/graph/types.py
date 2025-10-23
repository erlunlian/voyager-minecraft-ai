"""Type definitions for LangGraph state machine."""

from typing import List, Optional, TypedDict

from agents.types import Evaluation
from models import BotState, ExecutionResult, Skill


class VoyagerState(TypedDict):
    """State for LangGraph state machine (must be TypedDict for LangGraph)."""

    # Core task info
    task: str
    task_id: int
    iteration: int

    # Bot state
    bot_state_before: Optional[BotState]
    bot_state_after: Optional[BotState]

    # Agent outputs
    generated_code: str
    skills_retrieved: List[Skill]
    execution_result: Optional[ExecutionResult]
    critic_feedback: Optional[Evaluation]

    # Control flow
    success: bool
    retry_count: int
    should_continue: bool

    # Session info
    session_id: int
    completed_tasks: List[str]
    failed_tasks: List[str]
