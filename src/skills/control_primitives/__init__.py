"""
Control Primitives for Minecraft Bot

This package contains the low-level control primitives for the Minecraft bot,
based on the original Voyager paper implementation.

These primitives provide robust, error-handled actions that the bot can use
to interact with the Minecraft world. Each primitive includes:
- Parameter validation
- Error handling with fail counters
- Progress feedback via bot.chat()
- Checkpoint saving with bot.save()

Core Primitives:
- craftItem: Craft items using recipes
- mineBlock: Mine blocks with collectBlock API
- placeItem: Place blocks with proper reference checking
- smeltItem: Smelt items in furnaces
- killMob: Combat with melee or ranged weapons
- exploreUntil: Exploration with callback-based early stopping
- useChest functions: Chest interactions (get, deposit, check)
- shoot: Ranged weapon attacks

Helper Functions:
- failedCraftFeedback: Detailed crafting error messages
- waitForMobRemoved: Wait for mob death (melee)
- waitForMobShot: Wait for mob death (ranged)
- moveToChest, listItemsInChest, closeChest: Chest helpers
"""

__all__ = [
    "craftItem",
    "mineBlock",
    "placeItem",
    "smeltItem",
    "killMob",
    "exploreUntil",
    "getItemFromChest",
    "depositItemIntoChest",
    "checkItemInsideChest",
    "shoot",
]
