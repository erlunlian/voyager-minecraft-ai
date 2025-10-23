"""Critic Agent - Evaluates task completion and provides feedback."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from agents.prompts import CRITIC_SYSTEM_PROMPT
from agents.types import Evaluation
from models import BotState, ExecutionResult


class CriticAgent:
    """Evaluates whether a task was successfully completed."""

    def __init__(self, azure_api_key: str, azure_endpoint: str):
        self.llm = AzureChatOpenAI(
            model="gpt-5-nano",
            api_version="2025-04-01-preview",
            temperature=0,
            timeout=30,  # 30 second timeout
        )

        self.system_prompt = CRITIC_SYSTEM_PROMPT

    def evaluate(
        self,
        task: str,
        before_state: BotState,
        after_state: BotState,
        execution_result: ExecutionResult,
    ) -> Evaluation:
        """Evaluate task completion."""

        # Build evaluation context
        context = f"Task: {task}\n\n"

        # Compare states
        context += "BEFORE STATE:\n"
        context += self._format_state(before_state)
        context += "\n\nAFTER STATE:\n"
        context += self._format_state(after_state)

        # Add execution result
        context += "\n\nEXECUTION RESULT:\n"
        if execution_result.success:
            context += "Status: Success\n"
            if execution_result.result:
                context += f"Output: {execution_result.result}\n"
        else:
            context += "Status: Failed\n"
            context += f"Error: {execution_result.error or 'Unknown error'}\n"

        context += "\nEvaluate whether the task was completed successfully:"

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=context),
        ]

        response = self.llm.invoke(messages)

        # Parse JSON response
        import json

        try:
            eval_dict = json.loads(response.content)
            return Evaluation(
                success=eval_dict.get("success", False),
                reasoning=eval_dict.get("reasoning", ""),
                achievements=eval_dict.get("achievements", []),
                suggestions=eval_dict.get("suggestions", ""),
            )
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return Evaluation(
                success=execution_result.success,
                reasoning=response.content,
                achievements=[],
                suggestions="",
            )

    def _format_state(self, state: BotState) -> str:
        """Format bot state for comparison."""
        if not state:
            return "State unavailable"

        lines = []

        # Position
        pos = state.position
        lines.append(f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")

        # Health and food
        lines.append(f"Health: {state.health}/20")
        lines.append(f"Food: {state.food}/20")

        # Inventory
        if state.inventory:
            inv_items = {}
            for item in state.inventory:
                inv_items[item.name] = inv_items.get(item.name, 0) + item.count
            inv_str = ", ".join(
                [f"{count}x {name}" for name, count in sorted(inv_items.items())]
            )
            lines.append(f"Inventory: {inv_str}")
        else:
            lines.append("Inventory: Empty")

        return "\n".join(lines)
