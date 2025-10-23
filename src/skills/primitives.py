"""Primitive skills for Minecraft bot."""

import traceback
from pathlib import Path

from skills.skill_manager import SkillManager

# Get the directory where this file is located
SKILLS_DIR = Path(__file__).parent
CONTROL_PRIMITIVES_DIR = SKILLS_DIR / "control_primitives"


def load_js_file(filename: str) -> str:
    """Load a JavaScript file from the control_primitives directory."""
    filepath = CONTROL_PRIMITIVES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Control primitive not found: {filepath}")
    return filepath.read_text()


# Define primitive skills with their metadata
# The code will be loaded from the corresponding .js files
PRIMITIVE_SKILLS = [
    {
        "name": "mineBlock",
        "file": "mineBlock.js",
        "description": "Mine a specific type of block. Finds blocks within 32 blocks and mines them using the collectBlock API. Includes fail counter and saves checkpoint on success. Note: To get cobblestone, mine stone blocks (mineBlock(bot, 'cobblestone', count) will mine stone blocks to get cobblestone).",
        "parameters": ["name", "count"],
        "tags": ["mining", "basic", "resource"],
    },
    {
        "name": "craftItem",
        "file": "craftItem.js",
        "description": "Craft an item using a crafting table or inventory. Handles recipe lookup, crafting table navigation, and provides detailed feedback on missing ingredients.",
        "parameters": ["name", "count"],
        "tags": ["crafting", "basic"],
    },
    {
        "name": "placeItem",
        "file": "placeItem.js",
        "description": "Place a block at a specific position. Finds reference blocks, navigates to position, and handles placement with sophisticated error checking.",
        "parameters": ["name", "position"],
        "tags": ["building", "basic"],
    },
    {
        "name": "smeltItem",
        "file": "smeltItem.js",
        "description": "Smelt items in a furnace using specified fuel. Manages furnace operations, fuel consumption, and item smelting with detailed progress tracking.",
        "parameters": ["itemName", "fuelName", "count"],
        "tags": ["smelting", "crafting", "resource"],
    },
    {
        "name": "killMob",
        "file": "killMob.js",
        "description": "Kill a specific mob type. Supports both melee (pvp) and ranged weapons (hawkEye). Collects dropped items and saves checkpoint on success.",
        "parameters": ["mobName", "timeout"],
        "tags": ["combat", "entity", "mob"],
    },
    {
        "name": "exploreUntil",
        "file": "exploreUntil.js",
        "description": "Explore in a specific direction until a callback condition is met or timeout. Useful for finding resources, mobs, or biomes. Supports directional exploration with early stopping.",
        "parameters": ["direction", "maxTime", "callback"],
        "tags": ["exploration", "navigation", "callback"],
    },
    {
        "name": "getItemFromChest",
        "file": "useChest.js",
        "description": "Retrieve items from a chest at a specific position. Handles navigation, chest opening, and item withdrawal with error handling.",
        "parameters": ["chestPosition", "itemsToGet"],
        "tags": ["chest", "storage", "inventory"],
    },
    {
        "name": "depositItemIntoChest",
        "file": "useChest.js",
        "description": "Deposit items into a chest at a specific position. Handles navigation, chest opening, and item deposit with error handling.",
        "parameters": ["chestPosition", "itemsToDeposit"],
        "tags": ["chest", "storage", "inventory"],
    },
    {
        "name": "checkItemInsideChest",
        "file": "useChest.js",
        "description": "Check what items are inside a chest. Opens the chest and reports contents through bot events.",
        "parameters": ["chestPosition"],
        "tags": ["chest", "storage", "inventory"],
    },
    {
        "name": "shoot",
        "file": "shoot.js",
        "description": "Shoot a target entity with a ranged weapon (bow, crossbow, snowball, etc.). Uses hawkEye auto-attack system.",
        "parameters": ["weapon", "target"],
        "tags": ["combat", "ranged", "entity"],
    },
]


# Helper functions that are used by primitives
HELPER_SKILLS = [
    {
        "name": "failedCraftFeedback",
        "file": "craftHelper.js",
        "description": "Internal helper function that provides detailed feedback on why crafting failed, including missing ingredients.",
        "parameters": ["name", "item", "craftingTable"],
        "tags": ["helper", "crafting", "internal"],
    },
    {
        "name": "waitForMobRemoved",
        "file": "waitForMobRemoved.js",
        "description": "Internal helper function that waits for a mob to be killed and handles item drops. Used by killMob for melee combat.",
        "parameters": ["entity", "timeout"],
        "tags": ["helper", "combat", "internal"],
    },
    {
        "name": "waitForMobShot",
        "file": "waitForMobRemoved.js",
        "description": "Internal helper function that waits for a mob to be shot and handles item drops. Used by killMob for ranged combat.",
        "parameters": ["entity", "timeout"],
        "tags": ["helper", "combat", "internal"],
    },
    {
        "name": "moveToChest",
        "file": "useChest.js",
        "description": "Internal helper function that navigates to a chest position and validates it exists.",
        "parameters": ["chestPosition"],
        "tags": ["helper", "chest", "internal"],
    },
    {
        "name": "listItemsInChest",
        "file": "useChest.js",
        "description": "Internal helper function that lists items in a chest and emits events with the contents.",
        "parameters": ["chestBlock"],
        "tags": ["helper", "chest", "internal"],
    },
    {
        "name": "closeChest",
        "file": "useChest.js",
        "description": "Internal helper function that properly closes a chest after use.",
        "parameters": ["chestBlock"],
        "tags": ["helper", "chest", "internal"],
    },
    {
        "name": "givePlacedItemBack",
        "file": "givePlacedItemBack.js",
        "description": "Internal helper function used in testing to restore placed items.",
        "parameters": ["name", "position"],
        "tags": ["helper", "testing", "internal"],
    },
]


def load_primitive_skills(skill_manager: SkillManager, include_helpers: bool = False):
    """Load all primitive skills into the skill manager.

    Args:
        skill_manager: The skill manager to load skills into
        include_helpers: Whether to also load helper functions (default: False)
    """
    loaded = 0
    skills_to_load = PRIMITIVE_SKILLS.copy()

    if include_helpers:
        skills_to_load.extend(HELPER_SKILLS)

    for skill in skills_to_load:
        try:
            # Load the JavaScript code from file
            code = load_js_file(skill["file"])

            skill_manager.add_skill(
                name=skill["name"],
                description=skill["description"],
                code=code,
                parameters=skill["parameters"],
                tags=skill["tags"],
            )
            loaded += 1
            print(f"  ✓ Loaded {skill['name']}")
        except Exception as e:
            print(
                f"  ✗ Failed to load skill {skill['name']}: {e}\n{traceback.format_exc()}"
            )

    print(f"\n📦 Loaded {loaded}/{len(skills_to_load)} primitive skills")
    return loaded


def list_available_primitives():
    """List all available primitive skills."""
    print("\n=== Available Primitive Skills ===\n")

    print("Core Primitives:")
    for skill in PRIMITIVE_SKILLS:
        params = ", ".join(skill["parameters"])
        print(f"  • {skill['name']}({params})")
        print(f"    {skill['description']}")
        print(f"    Tags: {', '.join(skill['tags'])}\n")

    print("\nHelper Functions:")
    for skill in HELPER_SKILLS:
        params = ", ".join(skill["parameters"])
        print(f"  • {skill['name']}({params})")
        print(f"    {skill['description']}\n")


if __name__ == "__main__":
    # When run directly, list available primitives
    list_available_primitives()
