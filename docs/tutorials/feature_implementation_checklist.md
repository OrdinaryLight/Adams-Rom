# Feature implementation checklist

Use this checklist to add the requested features to this Emerald Expansion project. Each section names the lowest-risk implementation, the files that own the behavior, and a test that proves the feature works.

Do the data-only features first. Add the two battle-engine changes, fixed trainer rewards and team-wide level rewards, only after their data formats are settled. They touch shared trainer and experience code.

## Shared setup

1. Reserve one unused `FLAG_` constant for every permanent map object. Use one flag per barricade, ground-loot object, party heal, and static encounter.
2. Put reusable event scripts in an appropriate file under `data/scripts/`. Add text in `data/text/` and exports in `include/event_scripts.h` when another script file needs the label.
3. Add a small test map in Porymap. Place one instance of each feature there before adding content to production maps.
4. Build with `make` after each engine or graphics change. Test the resulting `pokeemerald.gba` in mGBA with a new save and with a save that has already collected the relevant object.

## 1. Sell a removable barricade

Use a blocking object event that hides when its event flag is set. Its script asks for payment, verifies the player's money, removes the money, and sets the flag. The map reload removes the object permanently.

1. Add a barricade graphic or reuse an existing blocking object graphic in Porymap.
2. Place a normal object event on the blocking tile. Give the event a unique local ID, its removal flag, and a script such as `EventScript_BuyBarricadeRemoval`.
3. In the script, show the price and ask the player to confirm. On confirmation, use `checkmoney PRICE`.
4. If `VAR_RESULT` is `FALSE`, show an insufficient-money message and end the script.
5. If the player can pay, call `removemoney PRICE`, then `setflag FLAG_BARRICADE_REMOVED`.
6. Refresh the current map object if the map does not hide it immediately. Leaving and re-entering the map must also hide it because the flag is set.

The script commands live in `asm/macros/event.inc`. `checkmoney` does not remove money, so keep it before `removemoney`.

**Done when:** the player cannot pass before payment, loses exactly the displayed amount after confirming, and the barricade stays gone after saving and reloading.

## 2. Add fixed and random ground-loot Poké Balls

Fixed item balls already exist. `Common_EventScript_FindItem` in `data/scripts/item_ball_scripts.inc` reads an item's ID and quantity from an item-ball map object. The object graphic is `OBJ_EVENT_GFX_ITEM_BALL`.

1. For fixed loot, add an item-ball object in Porymap. Set its item and amount fields, assign `Common_EventScript_FindItem`, and assign a unique event flag.
2. For a named fixed item with a custom message, add a script that calls `finditem ITEM_NAME amount`. The command displays the find-item message and sets the object's flag only when the bag has room.
3. For random loot, create `src/ground_loot.c` and `include/ground_loot.h`. Define constant item tables keyed by a small `enum GroundLootTableId`.
4. Add a field special or a `callnative` script command named `SelectGroundLoot`. It reads a table ID from `VAR_0x8000`, chooses one entry with `Random()`, and writes the selected item and quantity to `VAR_RESULT` and `VAR_0x8009`.
5. Register the special in `data/specials.inc`, or register the script command in `data/script_cmd_table.inc` and `asm/macros/event.inc`.
6. Make a reusable random-loot script: store the table ID, select the item, and call `finditem VAR_RESULT VAR_0x8009`. Give every random-loot object its own event flag.
7. Decide whether the random result changes after a full bag. The recommended behavior is to roll only after the bag-space check, or save the selected result in an event variable before the first `finditem` attempt. Do not silently replace a rolled item after the player sees its name.

`src/item_ball.c` contains the existing map-template lookup. Keep the random-table logic separate so normal item balls stay unchanged.

**Done when:** a fixed ball always gives its configured item, a random ball gives only entries from its configured table, and neither object disappears when the bag is full.

## 3. Make sightline trainers use random teams

The project already supports Trainer Party Pools. A pool randomizes individual Pokémon from one larger roster. Use it when the trainer needs a flexible party. Use several trainer IDs and pick one in the field script when the trainer must choose one complete, hand-authored team.

1. Create the trainer and its possible Pokémon in `src/data/trainers.party`, or use `src/data/trainers.h` if the project uses C trainer data.
2. For a party pool, define more Pokémon than `Party Size`. Set `Party Size` to the battle size and add the pool rules, tags, and optional copy-pool settings described in `docs/tutorials/how_to_trainer_party_pool.md`.
3. For whole-team randomization, create one trainer ID per complete team. Give each trainer the same name, class, portrait, AI, and battle text.
4. Make the sightline object a trainer event in Porymap. Set its trainer sight distance and point it to a script that chooses a team before calling `trainerbattle_single`.
5. In that script, call `random TEAM_COUNT`, branch on `VAR_RESULT`, and call the matching `trainerbattle_single TRAINER_NAME ...`. Let the normal trainer-battle setup handle walking toward the player and the defeated-trainer flag.
6. Give all variants the same encounter behavior. If one map object can select multiple trainer IDs, add a separate persistent flag for the map object instead of relying on each trainer ID's defeated flag.
7. Configure `B_POOL_SETTING_CONSISTENT_RNG` or `B_POOL_SETTING_USE_FIXED_SEED` in `include/config/battle.h` if repeatable pool selection matters for the project.

**Done when:** walking into the trainer's sight starts a battle, pool trainers draw only valid members, and whole-team trainers never mix Pokémon from different authored teams.

## 4. Add custom trainer sprites

"Trainer sprite" can mean an overworld object, a battle front portrait, or a player and partner back portrait. Add the image type that the feature needs. A normal NPC trainer usually needs an overworld object and a battle front portrait.

1. Create the front portrait as a PNG and palette in `graphics/trainers/front_pics/` and `graphics/trainers/palettes/`. The combined image and transparent color must use no more than 16 colors.
2. Register the front portrait and palette in `src/data/graphics/trainers.h`.
3. Add a `TRAINER_PIC_*` value before `TRAINER_PIC_FRONT_COUNT` in `include/constants/trainers.h`.
4. Add the matching `TRAINER_SPRITE(...)` entry in `gTrainerSprites` in `src/data/graphics/trainers.h`.
5. Set the trainer's `Pic:` field in `src/data/trainers.party`, or its `.trainerPic` field in `src/data/trainers.h`.
6. If the player or a battle partner needs a matching back portrait, follow `docs/tutorials/how_to_trainer_back_pic.md` and add it after `TRAINER_PIC_FRONT_COUNT`.
7. For an overworld sprite, add the graphics and `ObjectEventGraphicsInfo` entry under `src/data/object_events/`, add a new `OBJ_EVENT_GFX_*` constant in `include/constants/event_objects.h`, and add the pointer in `src/data/object_events/object_event_graphics_info_pointers.h`. Select that object graphic in Porymap.

The existing front-portrait guide is `docs/tutorials/how_to_trainer_front_pic.md`.

**Done when:** the trainer renders correctly on the map, in the battle introduction, and in every battle layout that uses that portrait.

## 5. Make ground-loot Poké Balls visibly different

Create separate object-event graphics for each visible loot category. Do not infer the reward from the sprite at runtime. The map object chooses both its graphic and its fixed or random loot script.

1. Decide the small, stable set of categories, such as medicine, Poké Balls, technical machines, key items, and unknown random loot.
2. Create a 16-color overworld graphic for each category. Keep the same dimensions and animation behavior as `gObjectEventGraphicsInfo_PokeBall`.
3. Add one `OBJ_EVENT_GFX_*` constant and one `ObjectEventGraphicsInfo` entry per category, following the object-event registration route in item 4.
4. Add each entry to `gObjectEventGraphicsInfoPointers` in `src/data/object_events/object_event_graphics_info_pointers.h`.
5. In Porymap, choose the matching graphic for each ground-loot object and keep its reward script separate from its appearance.
6. Add a short legend or an early in-game explanation if the colors or icons do not make the category obvious.

**Done when:** players can identify the loot category before interacting, and every custom ball uses the normal one-time item flag behavior.

## 6. Give trainers a fixed cash reward

Vanilla trainer payout is calculated from the trainer class and the last Pokémon's level in `GetTrainerMoneyToGive` in `src/battle_script_commands.c`. Add an optional override to the trainer data rather than changing a trainer class for one special battle.

1. Add a zero-default `u32 moneyReward` field to `struct Trainer` in `include/data.h`.
2. Extend `tools/trainerproc/main.c` and `src/data/trainers.party` syntax with `Money Reward:`. Keep zero as "use the normal calculation."
3. Set `.moneyReward = AMOUNT` for trainers that need a fixed payout.
4. In `GetTrainerMoneyToGive`, return `trainer->moneyReward` when it is nonzero. Keep Secret Base, multi-trainer, Amulet Coin, Happy Hour, and money-cap handling in the existing reward flow.
5. Test a normal trainer, a fixed-reward trainer, and a double battle. Confirm that a zero override still follows the vanilla formula.

**Done when:** the fixed-reward trainer gives the configured amount before existing payout multipliers, and unrelated trainers have unchanged payouts.

## 7. Add a one-time full-party heal

The project already exposes `HealPlayerParty` as a field special in `data/specials.inc`.

1. Place an object event with a unique event flag and a script such as `EventScript_OneTimePartyHeal`.
2. In the script, show the heal message, call `special HealPlayerParty`, then set the event flag.
3. Play a healing sound or animation before setting the flag if the map object needs feedback.
4. Use the same object flag in Porymap so the healer disappears after use.

`HealPlayerParty` is implemented in `src/script_pokemon_util.c`. It restores party members and uses the project's normal field-heal behavior.

**Done when:** fainted and statused party Pokémon recover, the object cannot be used again, and it remains gone after a reload.

## 8. Use better trainer AI

Use existing AI flags before adding new AI code. The project provides `AI_FLAG_BASIC_TRAINER` and `AI_FLAG_SMART_TRAINER` in `include/constants/battle_ai.h`.

1. Give ordinary competent trainers `AI: Basic Trainer` in `src/data/trainers.party`.
2. Give important trainers `AI: Smart Trainer`. Add a strategy-specific flag only when the team supports it, such as `Ace Pokemon`, `Prefer Baton Pass`, or `Powerful Status`.
3. Give every stronger AI trainer sensible moves, held items, abilities, and party order. AI flags cannot make a team with only weak or unusable moves play well.
4. For custom battle-specific scoring, use dynamic AI functions. Read `docs/tutorials/ai_dynamic_functions.md` before adding one.
5. Run repeated battles with the same team. Check that the trainer avoids obviously failing moves, switches only when it helps, and does not make a strategy worse with conflicting flags.

**Done when:** the intended trainer types use the chosen flag set and their battle behavior matches the team design.

## 9. Define the teams used by trainers

Use `src/data/trainers.party` unless the project deliberately uses `src/data/trainers.h`. The `.party` source is easier to review and supports party pools.

1. Add a unique trainer heading such as `=== TRAINER_ROUTE_TESTER ===`.
2. Set `Name`, `Class`, `Pic`, `Gender`, `Music`, `Double Battle`, and `AI`.
3. Add each Pokémon with its species, level, moves, held item, ability, nature, IVs, EVs, and any required pool tags.
4. Set `Party Size` to the exact number of Pokémon for a fixed team. For a party pool, set it below the number of defined Pokémon.
5. If several trainers use the same pool, use `Copy Pool:` instead of duplicating the Pokémon data.
6. Reference the trainer ID from the map's battle script with `trainerbattle_single`, `trainerbattle_double`, or the random-team selection script from item 3.
7. Build after editing trainer data. The trainer-data tooling validates the source as part of the build.

**Done when:** every team appears with the intended species, moves, levels, AI, portrait, and battle format.

## 10. Add a one-time wild encounter

Use a map object with an event flag. Set that flag before starting the battle so the encounter disappears as soon as the player enters it, including if they run away or lose.

1. Place an overworld Pokémon object in Porymap. Give it a unique event flag and an interaction script.
2. In the script, show the encounter text and confirm that the player wants to interact if needed.
3. Call `setflag FLAG_STATIC_MON_GONE` before `setwildbattle`.
4. Call `setwildbattle SPECIES level heldItem` and then `dowildbattle`.
5. End the script after the battle. The event flag hides the map object when the map refreshes or reloads.
6. Use `CreateScriptedWildMon` in `src/script_pokemon_util.c` only if the encounter needs properties that the standard script command cannot express.

**Done when:** the encounter starts once, does not reappear after fleeing or losing, and cannot be triggered again after saving and loading.

## 11. Give the whole party levels after specified trainer victories

This needs a battle-engine feature. Do not add experience directly to `MON_DATA_EXP` after battle. That skips the normal move-learning, stat recalculation, evolution, level-cap, and UI paths.

1. Add a zero-default `partyLevelReward` field to `struct Trainer` in `include/data.h`. Define `0` as no special reward and positive values as levels for every eligible party Pokémon.
2. Add `Party Level Reward:` to `tools/trainerproc/main.c` and `src/data/trainers.party` syntax. Keep the setting per trainer so ordinary trainer battles remain unchanged.
3. At battle setup, copy the trainer's reward into battle state. For two-trainer battles, define whether the rewards add or the larger value wins. Document the rule and test it.
4. In `Cmd_getexp` in `src/battle_script_commands.c`, skip the normal per-fainted-Pokémon experience flow only when the current trainer battle has a party-level reward.
5. Add a post-victory level-up queue that processes each eligible member of `gParties[B_TRAINER_PLAYER]` one level at a time. Reuse the normal experience-controller path in `src/battle_controller_player.c` where possible.
6. For each level, advance the Pokémon to the next value in `gExperienceTables`, recalculate stats, offer every level-up move through `MonTryLearningNewMove`, and run the normal evolution checks. Respect level 100 and the project's level-cap settings.
7. Run the queue only after a player victory. It must not run after fleeing, whiteout, link battles, Battle Frontier battles, or a trainer battle that has no reward.
8. Add automated tests for a Pokémon that learns a move, a Pokémon that evolves, a level-100 Pokémon, a fainted party member if it is ineligible by design, and a normal trainer battle with standard experience.

The normal battle experience entry point is `Cmd_getexp` in `src/battle_script_commands.c`. The player controller owns level-up presentation and data updates in `src/battle_controller_player.c`. `MonTryLearningNewMove` is declared in `include/pokemon.h`.

**Done when:** a configured trainer gives no experience for individual knockouts, each eligible party member gains the configured number of levels after victory, moves and evolutions work normally, and every other battle retains its normal experience behavior.
