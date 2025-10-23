"""Action Agent - Generates code to accomplish tasks."""

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from agents.prompts import ACTION_SYSTEM_PROMPT
from models import BotState, Skill


class ActionAgent:
    """Generates JavaScript code for Mineflayer bot to execute tasks."""

    def __init__(self, azure_api_key: str, azure_endpoint: str):
        self.llm = AzureChatOpenAI(
            model="gpt-5-nano",
            api_version="2025-04-01-preview",
            temperature=0,
        )

        self.system_prompt = ACTION_SYSTEM_PROMPT

    def generate_code(
        self,
        task: str,
        bot_state: BotState,
        relevant_skills: List[Skill] = None,
        code_from_last_round: str = None,
        execution_error: str = None,
        chat_log: List[str] = None,
        critique: str = None,
    ) -> str:
        """Generate code to accomplish the task."""

        # Format context in original Voyager format
        context = self._format_context(
            task=task,
            bot_state=bot_state,
            relevant_skills=relevant_skills,
            code_from_last_round=code_from_last_round,
            execution_error=execution_error,
            chat_log=chat_log,
            critique=critique,
        )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=context),
        ]

        response = self.llm.invoke(messages)
        code = self._extract_code(response.content)

        return code

    def _format_context(
        self,
        task: str,
        bot_state: BotState,
        relevant_skills: List[Skill] = None,
        code_from_last_round: str = None,
        execution_error: str = None,
        chat_log: List[str] = None,
        critique: str = None,
    ) -> str:
        """Format context in original Voyager format."""

        # Format inventory
        if bot_state.inventory:
            inv_items = []
            for item in bot_state.inventory:
                inv_items.append(f"{item.count}x {item.name}")
            inventory_str = ", ".join(inv_items)
            inventory_line = (
                f"Inventory ({len(bot_state.inventory)}/36): {inventory_str}"
            )
        else:
            inventory_line = "Inventory (0/36): Empty"

        # Format nearby entities
        if bot_state.nearby_entities:
            entities = []
            for entity in bot_state.nearby_entities[:10]:  # Limit to 10
                name = entity.name or "unknown"
                entities.append(f"{name} ({entity.distance:.1f}m)")
            entities_str = ", ".join(entities)
            entities_line = f"Nearby entities (nearest to farthest): {entities_str}"
        else:
            entities_line = "Nearby entities (nearest to farthest): None"

        # Format nearby blocks
        if bot_state.nearby_blocks:
            blocks = []
            for block_type, block_info in bot_state.nearby_blocks.items():
                blocks.append(f"{block_type} ({block_info.distance:.1f}m)")
            blocks_str = ", ".join(blocks)
            blocks_line = f"Nearby blocks: {blocks_str}"
        else:
            blocks_line = "Nearby blocks: None"

        # Format biome
        biome_names = {
            0: "ocean",
            1: "plains",
            2: "desert",
            3: "mountains",
            4: "forest",
            5: "taiga",
            6: "swamp",
            7: "river",
            8: "nether_wastes",
            9: "end_highlands",
            10: "end_midlands",
            11: "end_barrens",
            12: "end_void",
            13: "the_void",
            14: "beach",
            15: "desert_hills",
            16: "wooded_hills",
            17: "mountain_edge",
            18: "jungle",
            19: "jungle_hills",
            20: "jungle_edge",
            21: "deep_ocean",
            22: "stone_shore",
            23: "snowy_beach",
            24: "birch_forest",
            25: "birch_forest_hills",
            26: "dark_forest",
            27: "snowy_taiga",
            28: "snowy_taiga_hills",
            29: "giant_tree_taiga",
            30: "giant_tree_taiga_hills",
            31: "wooded_mountains",
            32: "savanna",
            33: "savanna_plateau",
            34: "badlands",
            35: "wooded_badlands_plateau",
            36: "badlands_plateau",
            37: "small_end_islands",
            38: "end_midlands",
            39: "end_highlands",
            40: "end_barrens",
            41: "warm_ocean",
            42: "lukewarm_ocean",
            43: "cold_ocean",
            44: "deep_warm_ocean",
            45: "deep_lukewarm_ocean",
            46: "deep_cold_ocean",
            47: "deep_ocean",
            48: "nether_wastes",
            49: "warped_forest",
            50: "crimson_forest",
            51: "soul_sand_valley",
            52: "basalt_deltas",
        }
        biome_name = (
            biome_names.get(bot_state.biome, "unknown")
            if bot_state.biome
            else "unknown"
        )

        # Format time (convert to Minecraft time format)
        time_of_day = int(bot_state.time) % 24000
        time_str = f"{time_of_day}/24000"

        # Format position
        pos = bot_state.position
        position_str = f"({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"

        # Format equipment (simplified - would need more detailed equipment tracking)
        equipment_str = "None"  # TODO: Add equipment tracking to BotState

        # Format chat log
        chat_str = "\n".join(chat_log) if chat_log else "None"

        # Format relevant skills as programs
        programs_str = ""
        if relevant_skills:
            programs_str = (
                "Here are some useful programs written with Mineflayer APIs.\n\n"
            )
            for skill in relevant_skills[:3]:  # Top 3 skills
                programs_str += f"// {skill.name}: {skill.description}\n"
                programs_str += f"{skill.code}\n\n"

        # Build complete context
        context = f"""{programs_str}At each round of conversation, I will give you
Code from the last round: {code_from_last_round or "None"}
Execution error: {execution_error or "None"}
Chat log: {chat_str}
Biome: {biome_name}
Time: {time_str}
{blocks_line}
{entities_line}
Health: {bot_state.health}/20
Hunger: {bot_state.food}/20
Position: {position_str}
Equipment: {equipment_str}
{inventory_line}
Chests: None
Task: {task}
Context: Current task is to {task.lower()}
Critique: {critique or "None"}"""

        return context

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response."""
        # Remove markdown code blocks if present
        if "```javascript" in response:
            code = response.split("```javascript")[1].split("```")[0]
        elif "```js" in response:
            code = response.split("```js")[1].split("```")[0]
        elif "```" in response:
            code = response.split("```")[1].split("```")[0]
        else:
            code = response

        return code.strip()
