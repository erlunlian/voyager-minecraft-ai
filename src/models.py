"""
Shared type definitions for the Voyager Minecraft AI system.

This module contains only types that are shared across multiple modules:
- Skill types (used by skill_manager, agents, graph)
- Bot state types (used by executor, agents, graph)
- Execution types (used by executor, critic, graph)

Module-specific types are defined in their respective modules:
- Agent types → src/agents/types.py
- Session types → src/session/types.py
- Graph state types → src/graph/types.py
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ============================================================================
# Skill Types
# ============================================================================


@dataclass
class Skill:
    """Represents a Minecraft bot skill."""

    id: str
    name: str
    description: str
    code: str
    parameters: List[str]
    tags: List[str]
    distance: Optional[float] = None  # For similarity search results


@dataclass
class SkillQuery:
    """Query parameters for skill retrieval."""

    query: str
    n_results: int = 5


# ============================================================================
# Bot State Types
# ============================================================================


@dataclass
class Position:
    """3D position in Minecraft world."""

    x: float
    y: float
    z: float


@dataclass
class InventoryItem:
    """Item in bot's inventory."""

    name: str
    count: int
    slot: int


@dataclass
class NearbyEntity:
    """Entity near the bot."""

    name: Optional[str]
    type: str
    position: Position
    distance: float


@dataclass
class NearbyBlock:
    """Block near the bot."""

    position: Position
    distance: float


@dataclass
class BotState:
    """Complete state of the Minecraft bot."""

    inventory: List[InventoryItem]
    position: Position
    health: float
    food: float
    game_mode: str
    nearby_entities: List[NearbyEntity]
    nearby_blocks: Dict[str, NearbyBlock]
    time: float
    biome: Optional[int]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotState":
        """Create BotState from dictionary."""
        return cls(
            inventory=[InventoryItem(**item) for item in data.get("inventory", [])],
            position=Position(**data.get("position", {"x": 0, "y": 0, "z": 0})),
            health=data.get("health", 0),
            food=data.get("food", 0),
            game_mode=data.get("gameMode", "survival"),
            nearby_entities=[
                NearbyEntity(
                    name=e.get("name"),
                    type=e.get("type", "unknown"),
                    position=Position(**e.get("position", {"x": 0, "y": 0, "z": 0})),
                    distance=e.get("distance", 0),
                )
                for e in data.get("nearbyEntities", [])
            ],
            nearby_blocks={
                k: NearbyBlock(
                    position=Position(**v.get("position", {"x": 0, "y": 0, "z": 0})),
                    distance=v.get("distance", 0),
                )
                for k, v in data.get("nearbyBlocks", {}).items()
            },
            time=data.get("time", 0),
            biome=data.get("biome"),
        )


# ============================================================================
# Execution Types
# ============================================================================


@dataclass
class ExecutionResult:
    """Result of code execution in Minecraft."""

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    stack: Optional[str] = None
