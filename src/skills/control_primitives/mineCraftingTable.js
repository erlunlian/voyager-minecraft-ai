async function mineCraftingTable(bot) {
    // Find the nearest crafting table
    const craftingTable = bot.findBlock({
        matching: mcData.blocksByName.crafting_table.id,
        maxDistance: 32,
    });
    
    if (!craftingTable) {
        bot.chat("No crafting table found nearby");
        return false;
    }
    
    bot.chat("Mining the crafting table to take it with me");
    try {
        await bot.dig(craftingTable);
        bot.chat("Successfully mined the crafting table");
        return true;
    } catch (err) {
        bot.chat(`Could not mine the crafting table: ${err.message}`);
        return false;
    }
}
