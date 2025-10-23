// Utility function to map requested items to the blocks that need to be mined
function getBlockToMine(requestedItem) {
    const blockMappings = {
        "oak_log": "oak_log",
        "oak logs": "oak_log", 
        "oak wood": "oak_log",
        "wood": "oak_log",
        "logs": "oak_log",
        "cobblestone": "stone"  // To get cobblestone, mine stone blocks
    };
    
    return blockMappings[requestedItem] || requestedItem;
}

// Utility function to get the item name to check in inventory after mining
function getInventoryItemName(requestedItem) {
    const inventoryMappings = {
        "cobblestone": "cobblestone"  // When mining stone for cobblestone, check for cobblestone in inventory
    };
    
    return inventoryMappings[requestedItem] || requestedItem;
}

// Utility function to get the success message for collected items
function getCollectionMessage(requestedItem, totalCollected, blockName) {
    const messageMappings = {
        "cobblestone": `Collected ${totalCollected} cobblestone from mining stone blocks`
    };
    
    return messageMappings[requestedItem] || `Collected ${totalCollected} ${requestedItem} blocks`;
}

// Utility function to get the success message for mining completion
function getSuccessMessage(requestedItem, count) {
    const successMappings = {
        "cobblestone": `Successfully mined ${count} stone blocks to get cobblestone`
    };
    
    return successMappings[requestedItem] || `Successfully mined ${count} ${requestedItem} blocks`;
}

// Utility function to get the save checkpoint name
function getSaveCheckpointName(requestedItem) {
    const checkpointMappings = {
        "cobblestone": "cobblestone_mined"
    };
    
    return checkpointMappings[requestedItem] || `${requestedItem}_mined`;
}

// Utility function to get the error message for mining failures
function getErrorMessage(requestedItem, blockName) {
    const errorMappings = {
        "cobblestone": `Failed to mine stone blocks for cobblestone`
    };
    
    return errorMappings[requestedItem] || `Failed to mine ${blockName}`;
}

async function mineBlock(bot, name, count = 1) {
    // return if name is not string
    if (typeof name !== "string") {
        throw new Error(`name for mineBlock must be a string`);
    }
    if (typeof count !== "number") {
        throw new Error(`count for mineBlock must be a number`);
    }
    
    // Get the block name to mine and the item name to check in inventory
    const blockName = getBlockToMine(name);
    const inventoryItemName = getInventoryItemName(name);
    
    const blockByName = mcData.blocksByName[blockName];
    if (!blockByName) {
        throw new Error(`No block named ${blockName} (tried: ${name})`);
    }
    bot.chat(`Looking for ${blockName} blocks...`);
    const blocks = bot.findBlocks({
        matching: [blockByName.id],
        maxDistance: 32,
        count: 1024,
    });
    bot.chat(`Found ${blocks.length} ${blockName} blocks`);
    
    if (blocks.length === 0) {
        bot.chat(`No ${blockName} nearby, exploring to find some...`);
        
        // Try to find blocks by moving around
        const directions = [
            { x: 1, y: 0, z: 0 },
            { x: -1, y: 0, z: 0 },
            { x: 0, y: 0, z: 1 },
            { x: 0, y: 0, z: -1 },
            { x: 1, y: 0, z: 1 },
            { x: -1, y: 0, z: -1 }
        ];
        
        for (const dir of directions) {
            const newPos = bot.entity.position.offset(dir.x * 16, 0, dir.z * 16);
            bot.chat(`Checking position ${newPos.x}, ${newPos.y}, ${newPos.z}`);
            
            // Move to new position
            try {
                // Use safer goal setting to avoid conflicts
                if (bot.setGoalSafely) {
                    await bot.setGoalSafely(new goals.GoalXZ(newPos.x, newPos.z));
                } else {
                    await bot.pathfinder.goto(new goals.GoalXZ(newPos.x, newPos.z));
                }
                
                // Check for blocks at new position
                const newBlocks = bot.findBlocks({
                    matching: [blockByName.id],
                    maxDistance: 32,
                    count: 1024,
                });
                
                if (newBlocks.length > 0) {
                    bot.chat(`Found ${newBlocks.length} ${blockName} blocks at new position`);
                    blocks.push(...newBlocks);
                    break;
                }
            } catch (error) {
                bot.chat(`Could not reach position: ${error.message}`);
                continue;
            }
        }
        
        if (blocks.length === 0) {
            // Initialize fail counter if not exists
            if (typeof _mineBlockFailCount === 'undefined') {
                _mineBlockFailCount = 0;
            }
            _mineBlockFailCount++;
            if (_mineBlockFailCount > 10) {
                throw new Error(
                    "mineBlock failed too many times, make sure you explore before calling mineBlock"
                );
            }
            throw new Error(`No ${blockName} blocks found after exploration`);
        }
    }
    
    const targets = [];
    for (let i = 0; i < Math.min(blocks.length, count * 2); i++) { // Limit targets to avoid too many
        targets.push(bot.blockAt(blocks[i]));
    }
    
    bot.chat(`Mining ${Math.min(targets.length, count)} ${blockName} blocks...`);
    
    try {
        await bot.collectBlock.collect(targets, {
            ignoreNoPath: true,
            count: count,
        });
        
        // Wait a moment for items to be collected
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Check if we actually got the items
        const inventory = bot.inventory.items();
        const collectedItems = inventory.filter(item => item.name === inventoryItemName);
        const totalCollected = collectedItems.reduce((sum, item) => sum + item.count, 0);
        
        // Show collection message
        bot.chat(getCollectionMessage(name, totalCollected, blockName));
        
        if (totalCollected < count) {
            throw new Error(`Only collected ${totalCollected} ${inventoryItemName}, needed ${count}`);
        }
        
        // Show success message and save checkpoint
        bot.chat(getSuccessMessage(name, count));
        bot.save(getSaveCheckpointName(name));
    } catch (error) {
        bot.chat(`${getErrorMessage(name, blockName)}: ${error.message}`);
        throw error;
    }
}

