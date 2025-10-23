"""Type definitions for agent-specific models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Evaluation:
    """Evaluation result from critic agent."""

    success: bool
    reasoning: str
    achievements: List[str] = field(default_factory=list)
    suggestions: str = ""
    score: Optional[float] = None
