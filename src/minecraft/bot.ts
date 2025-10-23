import minecraftData from "minecraft-data";
import hawkEye from "minecrafthawkeye";
import mineflayer, { Bot } from "mineflayer";
import { plugin as collectBlock } from "mineflayer-collectblock";
import { Movements, goals, pathfinder } from "mineflayer-pathfinder";
import { plugin as pvp } from "mineflayer-pvp";
import { Vec3 } from "vec3";

interface BotConfig {
  host?: string;
  port?: number;
  username?: string;
  version?: string;
}

interface InventoryItem {
  name: string;
  count: number;
  slot: number;
}

interface NearbyEntity {
  name: string | undefined;
  type: string;
  position: Vec3;
  distance: number;
}

interface NearbyBlock {
  position: Vec3;
  distance: number;
}

interface BotState {
  inventory: InventoryItem[];
  position: { x: number; y: number; z: number };
  health: number;
  food: number;
  gameMode: string;
  nearbyEntities: NearbyEntity[];
  nearbyBlocks: Record<string, NearbyBlock>;
  time: number;
  biome: number | null;
}

interface ExecutionResult {
  success: boolean;
  result?: any;
  error?: string;
  stack?: string;
}

interface Message {
  type: string;
  data: any;
}

interface ExecutionContext {
  bot: Bot;
  mcData: any;
  Vec3: typeof Vec3;
  goals: typeof goals;
  pathfinder: any;
  sleep: (ms: number) => Promise<void>;
  log: (msg: string) => void;
  error: (msg: string) => void;
  // Global fail counters for primitives
  _craftItemFailCount: number;
  _mineBlockFailCount: number;
  _placeItemFailCount: number;
  _smeltItemFailCount: number;
  _killMobFailCount: number;
  // Goal types
  GoalNear: any;
  GoalXZ: any;
  GoalNearXZ: any;
  GoalBlock: any;
  GoalGetToBlock: any;
  GoalFollow: any;
  GoalPlaceBlock: any;
  GoalLookAtBlock: any;
}

class MinecraftBot {
  private config: BotConfig;
  private bot: Bot | null;
  private ready: boolean;

  constructor(config: BotConfig) {
    this.config = config;
    this.bot = null;
    this.ready = false;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.bot = mineflayer.createBot({
          host: this.config.host || "localhost",
          port: this.config.port || 25565,
          username: this.config.username || "VoyagerBot",
          version: this.config.version, // undefined = Auto-detect
        });

        // Load plugins
        this.bot.loadPlugin(pathfinder);
        this.bot.loadPlugin(collectBlock);
        this.bot.loadPlugin(pvp);
        this.bot.loadPlugin(hawkEye);

        // Setup event handlers
        this.bot.once("spawn", () => {
          console.log("Bot spawned in Minecraft");
          this.ready = true;

          if (this.bot) {
            // Initialize pathfinder
            const mcData = minecraftData(this.bot.version);
            const defaultMove = new Movements(this.bot);
            (this.bot as any).pathfinder.setMovements(defaultMove);
          }

          resolve();
        });

        this.bot.on("error", (err: Error) => {
          console.error("Bot error:", err);
          reject(err);
        });

        this.bot.on("kicked", (reason: string) => {
          console.log("Bot kicked:", reason);
        });

        this.bot.on("death", () => {
          console.log("Bot died");
          this.sendMessage({ type: "death", data: null });
        });

        this.bot.on("messagestr", (message: string) => {
          console.log("Chat:", message);
          // Send chat message to Python for context
          this.sendMessage({ type: "chat", data: message });
        });
      } catch (err) {
        reject(err);
      }
    });
  }

  getState(): BotState | null {
    if (!this.bot || !this.ready) {
      return null;
    }

    const inventory: InventoryItem[] = this.bot.inventory
      .items()
      .map((item) => ({
        name: item.name,
        count: item.count,
        slot: item.slot,
      }));

    const position = this.bot.entity.position;
    const health = this.bot.health;
    const food = this.bot.food;
    const gameMode = this.bot.game.gameMode;

    // Get nearby entities
    const nearbyEntities: NearbyEntity[] = Object.values(this.bot.entities)
      .filter(
        (e) => e !== this.bot!.entity && e.position.distanceTo(position) < 16
      )
      .map((e) => ({
        name: e.name || e.displayName,
        type: e.type,
        position: e.position,
        distance: e.position.distanceTo(position),
      }))
      .slice(0, 20); // Limit to 20 nearest

    // Get nearby blocks (simplified)
    const nearbyBlocks: Record<string, NearbyBlock> = {};
    try {
      const blockTypes = [
        "wood",
        "stone",
        "iron_ore",
        "coal_ore",
        "diamond_ore",
        "crafting_table",
      ];
      for (const blockType of blockTypes) {
        const block = this.bot.findBlock({
          matching: (b: any) => b.name.includes(blockType),
          maxDistance: 32,
        });
        if (block) {
          nearbyBlocks[blockType] = {
            position: block.position,
            distance: block.position.distanceTo(position),
          };
        }
      }
    } catch (err) {
      // Ignore errors in block finding
    }

    return {
      inventory,
      position: { x: position.x, y: position.y, z: position.z },
      health,
      food,
      gameMode,
      nearbyEntities: nearbyEntities.slice(0, 10),
      nearbyBlocks,
      time: this.bot.time.timeOfDay,
      biome: (this.bot.world as any).getBiome
        ? (this.bot.world as any).getBiome(position)
        : null,
    };
  }

  async executeCode(
    code: string,
    timeout: number = 60000
  ): Promise<ExecutionResult> {
    return new Promise(async (resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error("Code execution timeout"));
      }, timeout);

      try {
        if (!this.bot) {
          throw new Error("Bot not initialized");
        }

        // Create execution context with bot and helper functions
        const context: ExecutionContext = {
          bot: this.bot,
          mcData: minecraftData(this.bot.version),
          Vec3: Vec3,
          goals: goals,
          pathfinder: (this.bot as any).pathfinder,

          // Helper functions
          sleep: (ms: number) =>
            new Promise((resolve) => setTimeout(resolve, ms)),

          log: (msg: string) => {
            console.log("[Bot]", msg);
          },

          error: (msg: string) => {
            console.error("[Bot Error]", msg);
          },

          // Global fail counters for primitives
          _craftItemFailCount: 0,
          _mineBlockFailCount: 0,
          _placeItemFailCount: 0,
          _smeltItemFailCount: 0,
          _killMobFailCount: 0,

          // Goal types from mineflayer-pathfinder
          GoalNear: goals.GoalNear,
          GoalXZ: goals.GoalXZ,
          GoalNearXZ: goals.GoalNearXZ,
          GoalBlock: goals.GoalBlock,
          GoalGetToBlock: goals.GoalGetToBlock,
          GoalFollow: goals.GoalFollow,
          GoalPlaceBlock: goals.GoalPlaceBlock,
          GoalLookAtBlock: goals.GoalLookAtBlock,
        };

        // Add bot.save() helper function for checkpointing
        (this.bot as any).save = (checkpoint: string) => {
          console.log(`[Checkpoint] ${checkpoint}`);
          this.sendMessage({ type: "checkpoint", data: checkpoint });
        };

        // Add goal synchronization helper
        (this.bot as any).setGoalSafely = async (goal: any) => {
          const pathfinder = (this.bot as any).pathfinder;
          try {
            if (pathfinder.isMoving()) {
              pathfinder.setGoal(null);
              await new Promise((resolve) => setTimeout(resolve, 100));
            }
            pathfinder.setGoal(goal);
            await new Promise((resolve) => setTimeout(resolve, 200));
          } catch (error) {
            const errorMessage =
              error instanceof Error ? error.message : String(error);
            console.log(
              `[Bot] Goal setting conflict resolved: ${errorMessage}`
            );
            // Retry once after a short delay
            await new Promise((resolve) => setTimeout(resolve, 500));
            pathfinder.setGoal(goal);
          }
        };

        // Wrap code in async function and provide context
        const asyncCode = `
                    (async function() {
                        const { 
                            bot, mcData, Vec3, goals, pathfinder, sleep, log, error,
                            _craftItemFailCount, _mineBlockFailCount, _placeItemFailCount, 
                            _smeltItemFailCount, _killMobFailCount,
                            GoalNear, GoalXZ, GoalNearXZ, GoalBlock, GoalGetToBlock, 
                            GoalFollow, GoalPlaceBlock, GoalLookAtBlock
                        } = context;
                        
                        // Helper functions that primitives might use
                        ${this.getHelperFunctions()}
                        
                        ${code}
                    })()
                `;

        // Execute code with context
        let result;
        try {
          result = await eval(asyncCode);
        } catch (execError) {
          throw execError;
        }

        clearTimeout(timeoutId);
        resolve({ success: true, result });
      } catch (err: any) {
        clearTimeout(timeoutId);
        reject({ success: false, error: err.message, stack: err.stack });
      }
    });
  }

  loadControlPrimitive(name: string): string {
    try {
      const fs = require("fs");
      const path = require("path");
      // The compiled bot.js is in dist/minecraft/, so we need to go up to src/skills/control_primitives/
      const primitivePath = path.join(
        __dirname,
        "..",
        "..",
        "src",
        "skills",
        "control_primitives",
        `${name}.js`
      );
      const content = fs.readFileSync(primitivePath, "utf8");
      return content;
    } catch (error) {
      console.error(`Failed to load control primitive ${name}:`, error);
      // Return a safe fallback function instead of just a comment
      return `async function ${name}(bot, ...args) {
        console.error("Control primitive ${name} failed to load");
        throw new Error("Control primitive ${name} is not available");
      }`;
    }
  }

  getHelperFunctions(): string {
    // Load helper functions that primitives might use
    return `
      // Control primitives - load from files
      ${this.loadControlPrimitive("mineBlock")}
      ${this.loadControlPrimitive("craftItem")}
      ${this.loadControlPrimitive("placeItem")}
      ${this.loadControlPrimitive("smeltItem")}
      ${this.loadControlPrimitive("killMob")}
      ${this.loadControlPrimitive("exploreUntil")}
      ${this.loadControlPrimitive("useChest")}
      ${this.loadControlPrimitive("shoot")}
      ${this.loadControlPrimitive("mineCraftingTable")}
      
      // Helper function for combat - waits for mob to be killed in melee
      function waitForMobRemoved(bot, entity, timeout = 300) {
        return new Promise((resolve, reject) => {
          let success = false;
          let droppedItem = null;
          const timeoutId = setTimeout(() => {
            success = false;
            bot.pvp.stop();
          }, timeout * 1000);

          function onEntityGone(e) {
            if (e === entity) {
              success = true;
              clearTimeout(timeoutId);
              bot.chat(\`Killed \${entity.name}!\`);
              bot.pvp.stop();
            }
          }

          function onItemDrop(item) {
            if (entity.position.distanceTo(item.position) <= 1) {
              droppedItem = item;
            }
          }

          function onStoppedAttacking() {
            clearTimeout(timeoutId);
            bot.removeListener("entityGone", onEntityGone);
            bot.removeListener("stoppedAttacking", onStoppedAttacking);
            bot.removeListener("itemDrop", onItemDrop);
            if (!success) reject(new Error(\`Failed to kill \${entity.name}.\`));
            else resolve(droppedItem);
          }

          bot.on("entityGone", onEntityGone);
          bot.on("stoppedAttacking", onStoppedAttacking);
          bot.on("itemDrop", onItemDrop);
        });
      }

      // Helper function for combat - waits for mob to be shot
      function waitForMobShot(bot, entity, timeout = 300) {
        return new Promise((resolve, reject) => {
          let success = false;
          let droppedItem = null;
          const timeoutId = setTimeout(() => {
            success = false;
            bot.hawkEye.stop();
          }, timeout * 1000);

          function onEntityGone(e) {
            if (e === entity) {
              success = true;
              clearTimeout(timeoutId);
              bot.chat(\`Shot \${entity.name}!\`);
              bot.hawkEye.stop();
            }
          }

          function onItemDrop(item) {
            if (entity.position.distanceTo(item.position) <= 1) {
              droppedItem = item;
            }
          }

          function onAutoShotStopped() {
            clearTimeout(timeoutId);
            bot.removeListener("entityGone", onEntityGone);
            bot.removeListener("auto_shot_stopped", onAutoShotStopped);
            bot.removeListener("itemDrop", onItemDrop);
            if (!success) reject(new Error(\`Failed to shoot \${entity.name}.\`));
            else resolve(droppedItem);
          }

          bot.on("entityGone", onEntityGone);
          bot.on("auto_shot_stopped", onAutoShotStopped);
          bot.on("itemDrop", onItemDrop);
        });
      }

      // Helper function for crafting - provides detailed feedback on missing ingredients
      function failedCraftFeedback(bot, name, item, craftingTable) {
        const recipes = bot.recipesAll(item.id, null, craftingTable);
        if (!recipes.length) {
          throw new Error(\`No crafting table nearby\`);
        } else {
          const recipes = bot.recipesAll(item.id, null, mcData.blocksByName.crafting_table.id);
          var min = 999;
          var min_recipe = null;
          for (const recipe of recipes) {
            const delta = recipe.delta;
            var missing = 0;
            for (const delta_item of delta) {
              if (delta_item.count < 0) {
                const inventory_item = bot.inventory.findInventoryItem(
                  mcData.items[delta_item.id].name, null
                );
                if (!inventory_item) {
                  missing += -delta_item.count;
                } else {
                  missing += Math.max(-delta_item.count - inventory_item.count, 0);
                }
              }
            }
            if (missing < min) {
              min = missing;
              min_recipe = recipe;
            }
          }
          const delta = min_recipe.delta;
          let message = "";
          for (const delta_item of delta) {
            if (delta_item.count < 0) {
              const inventory_item = bot.inventory.findInventoryItem(
                mcData.items[delta_item.id].name, null
              );
              if (!inventory_item) {
                message += \` \${-delta_item.count} more \${mcData.items[delta_item.id].name}, \`;
              } else {
                if (inventory_item.count < -delta_item.count) {
                  message += \`\${-delta_item.count - inventory_item.count} more \${mcData.items[delta_item.id].name}\`;
                }
              }
            }
          }
          bot.chat(\`I cannot make \${name} because I need: \${message}\`);
        }
      }

      // Helper functions for chest interactions
      async function moveToChest(bot, chestPosition) {
        if (!(chestPosition instanceof Vec3)) {
          throw new Error("chestPosition for moveToChest must be a Vec3");
        }
        if (chestPosition.distanceTo(bot.entity.position) > 32) {
          bot.chat(\`/tp \${chestPosition.x} \${chestPosition.y} \${chestPosition.z}\`);
          await bot.waitForTicks(20);
        }
        const chestBlock = bot.blockAt(chestPosition);
        if (chestBlock.name !== "chest") {
          bot.emit("removeChest", chestPosition);
          throw new Error(\`No chest at \${chestPosition}, it is \${chestBlock.name}\`);
        }
        await bot.pathfinder.goto(new GoalLookAtBlock(chestBlock.position, bot.world, {}));
        return chestBlock;
      }

      async function listItemsInChest(bot, chestBlock) {
        const chest = await bot.openContainer(chestBlock);
        const items = chest.containerItems();
        if (items.length > 0) {
          const itemNames = items.reduce((acc, obj) => {
            if (acc[obj.name]) {
              acc[obj.name] += obj.count;
            } else {
              acc[obj.name] = obj.count;
            }
            return acc;
          }, {});
          bot.emit("closeChest", itemNames, chestBlock.position);
        } else {
          bot.emit("closeChest", {}, chestBlock.position);
        }
        return chest;
      }

      async function closeChest(bot, chestBlock) {
        try {
          const chest = await listItemsInChest(bot, chestBlock);
          await chest.close();
        } catch (err) {
          await bot.closeWindow(chestBlock);
        }
      }
    `;
  }

  sendMessage(message: Message): void {
    // Send message to Python via stdout
    console.log("MESSAGE:", JSON.stringify(message));
  }

  disconnect(): void {
    if (this.bot) {
      this.bot.quit();
      this.bot = null;
      this.ready = false;
    }
  }
}

// Handle messages from Python
process.stdin.setEncoding("utf8");
let buffer = "";

process.stdin.on("data", async (chunk: string) => {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop() || ""; // Keep incomplete line in buffer

  for (const line of lines) {
    if (!line.trim()) continue;

    try {
      const message: Message = JSON.parse(line);
      await handleMessage(message);
    } catch (err) {
      console.error("Error parsing message:", err);
    }
  }
});

let botInstance: MinecraftBot | null = null;

async function handleMessage(message: Message): Promise<void> {
  const { type, data } = message;

  try {
    switch (type) {
      case "connect":
        botInstance = new MinecraftBot(data);
        await botInstance.connect();
        botInstance.sendMessage({ type: "connected", data: null });
        break;

      case "get_state":
        const state = botInstance ? botInstance.getState() : null;
        if (botInstance) {
          botInstance.sendMessage({ type: "state", data: state });
        }
        break;

      case "execute":
        if (botInstance) {
          const result = await botInstance.executeCode(data.code, data.timeout);
          botInstance.sendMessage({ type: "execution_result", data: result });
        }
        break;

      case "disconnect":
        if (botInstance) {
          botInstance.disconnect();
          botInstance.sendMessage({ type: "disconnected", data: null });
          botInstance = null;
        }
        break;

      default:
        console.error("Unknown message type:", type);
    }
  } catch (err: any) {
    if (botInstance) {
      botInstance.sendMessage({
        type: "error",
        data: { message: err.message, stack: err.stack },
      });
    }
  }
}

// Handle process termination
process.on("SIGINT", () => {
  if (botInstance) {
    botInstance.disconnect();
  }
  process.exit(0);
});

console.log("Minecraft bot bridge ready");
