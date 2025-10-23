"""Curriculum Agent - Proposes tasks based on bot progress."""

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from agents.prompts import CURRICULUM_SYSTEM_PROMPT
from models import BotState


class CurriculumAgent:
    """Proposes progressive tasks for the bot to complete."""

    def __init__(self, azure_api_key: str, azure_endpoint: str):
        self.llm = AzureChatOpenAI(
            model="gpt-5-nano",
            api_version="2025-04-01-preview",
            temperature=0,
        )

        self.system_prompt = CURRICULUM_SYSTEM_PROMPT

    def propose_task(
        self,
        bot_state: BotState,
        completed_tasks: List[str] = None,
        failed_tasks: List[str] = None,
    ) -> str:
        """Propose next task based on bot state and history."""

        # Format bot state for the LLM
        inventory_summary = self._format_inventory(bot_state.inventory)
        position = bot_state.position
        health = bot_state.health
        food = bot_state.food

        # Build context
        context = f"""Current Bot State:
- Position: ({position.x:.1f}, {position.y:.1f}, {position.z:.1f})
- Health: {health}/20
- Food: {food}/20
- Inventory: {inventory_summary}
"""

        if completed_tasks:
            context += "\nRecently Completed Tasks:\n"
            for task in completed_tasks[-5:]:  # Last 5 tasks
                context += f"- {task}\n"

        if failed_tasks:
            context += "\nRecently Failed Tasks:\n"
            for task in failed_tasks[-3:]:  # Last 3 failures
                context += f"- {task}\n"

        context += "\nPropose the next task for the bot:"

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=context),
        ]

        response = self.llm.invoke(messages)
        task = response.content.strip()

        return task

    def _format_inventory(self, inventory: List) -> str:
        """Format inventory for display."""
        if not inventory:
            return "Empty"

        # Group by item type
        items = {}
        for item in inventory:
            items[item.name] = items.get(item.name, 0) + item.count

        # Format as string
        if not items:
            return "Empty"

        summary = ", ".join(
            [f"{count}x {name}" for name, count in sorted(items.items())]
        )
        return summary if summary else "Empty"
