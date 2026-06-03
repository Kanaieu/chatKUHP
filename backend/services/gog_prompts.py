PROMPTS = {}

PROMPTS["tuple_delimiter"] = "<|>"
PROMPTS["record_delimiter"] = "##"
PROMPTS["completion_delimiter"] = "<LIST_COMPLETE>"

PROMPTS["goal_extraction"] = """-Goal-
Given a portion of a document and relevant in-game recipes about the game Minecraft, extract actionable in-game goals that a player can achieve. Use only the content from the given document and in-game recipe JSONs to construct goals and subgoals. Do not infer or add goals beyond what is explicitly described. Focus solely on the core Minecraft experience. Exclude any content related to Minecraft spinoff games (e.g., Minecraft Dungeons, Minecraft Legends).

-Steps-
1. Identify relevant goals that a player can achieve in the game. For each goal, extract the following attributes:
- name: Name of the goal. Use short, specific names in the form of "<action> <minecraft_item>", such as "craft planks", "mine cobblestone", or "smelt charcoal". For tools with different grades such as "wooden" or "stone", use "<action> <grade> <minecraft_tool>", such as "craft a wooden pickaxe" or "craft a stone sword".
- description: A concise explanation of what the goal entails.
- req_tools: Needed tools to complete the goal, as a JSON object where keys are Minecraft tools and values are 1. For tools with multiple grades (e.g. wooden or stone), specify the tool grade and only include the lowest grade needed. Crafting tables and furnaces are considered as tools, and their usage can be determined by document text, recipes, and summaries. Smelting using a furnace always requires "fuel" as a tool. Use "None" (just as a standalone string, not as a JSON object or set or list) if no tools are needed.
- req_materials: Needed materials to complete the goal, as a JSON object where keys are Minecraft items and values are needed quantities of that item. If no materials are needed, set this to "None" (just as a standalone string, not as a JSON object or set or list).
- postconditions: The resulting state or item after completing the goal, as a JSON object where the keys are Minecraft items and values are the quantity. If there are no post-conditions, set this to "None" (just as a standalone string, not as a JSON object or set or list).
Before writing each goal, generate reasoning as to where the information about the goal comes from. If it comes from a shaped crafting recipe, you must use the format as described above, otherwise write a brief sentence.
Format each goal as a tuple: ("goal"{tuple_delimiter}"<name>"{tuple_delimiter}"<description>"{tuple_delimiter}"<req_tools>"{tuple_delimiter}"<req_materials>"{tuple_delimiter}"<postconditions>")

2. From the goals identified in step 1, identify subgoals that are needed for the achievement of the goal. For every goal, establish subgoal relationships between the goal and associated subgoals for each required material and tool that must be obtained or crafted, as identified by <req_tools> or <req_materials>.
For each goal-subgoal relationship, extract the following information:
- goal_name: Name of the higher-level goal, which must exist in the goals identified in step 1.
- subgoal_name: Name of the subgoal that is used by the goal.
- relationship_description: Explanation as to how and why the higher-level goal and the subgoal are related to each other.
Format each relationship as a tuple: ("subgoal"{tuple_delimiter}"<goal_name>"{tuple_delimiter}"<subgoal_name>"{tuple_delimiter}"<relationship_description>")

3. Return a single list of tuples of all goals and subgoals as extracted from steps 1 and 2. Use **{record_delimiter}** as the list delimiter. If either tools or materials are ambiguous or missing, omit the goal. Do not repeat the same goal in the list.

4. When finished, output {completion_delimiter}.

Only output the list as instructed without any explanation, summary, or other text. If there is no relevant information in the document, just output {completion_delimiter}.

Here are some examples:
######################
-Example 1-
######################
Document Text:
Log
This article is about the block found in trees and huge fungi. For the block crafted from logs or stems, see Planks. For the block that has the "bark" texture on all 6 sides, see Wood. For the file, see Tutorials/How to get a crash report.
A log or stem is a naturally occurring block found in trees or huge fungi, primarily used as a building block, and to create planks, a versatile crafting ingredient. It comes in nine types: oak, spruce, birch, jungle, acacia, dark oak, mangroveâ€Œ[upcoming: JE 1.19], crimson and warped.
A stripped log or stripped stem is a variant obtained by using an axe on a log or a stem respectively. Once stripped, it cannot be reversed.

Obtaining
Breaking
Logs and stems can be broken by hand, but using an axe speeds up the process. Logs and stems drop themselves when broken with any tool.

--- Recipe ---
{{
    "type": "minecraft:crafting_shaped",
    "group": "sticks",
    "pattern": [
        "#",
        "#"
    ],
    "key": {{
        "#": {{
            "tag": "minecraft:planks"
        }}
    }},
    "result": {{
        "item": "minecraft:stick",
        "count": 4
    }}
}}
Shaped Summary:
{{
    "crafting_table": false,
    "materials": {{
        "minecraft:planks": 2
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shaped",
    "pattern": [
        "##",
        "##"
    ],
    "key": {{
        "#": {{
            "tag": "minecraft:planks"
        }}
    }},
    "result": {{
        "item": "minecraft:crafting_table"
    }}
}}
Shaped Summary:
{{
    "crafting_table": false,
    "materials": {{
        "minecraft:planks": 4
    }}
}}
--- Recipe ---
{{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "X",
    "#"
  ],
  "key": {{
    "#": {{
      "item": "minecraft:stick"
    }},
    "X": {{
      "tag": "minecraft:coals"
    }}
  }},
  "result": {{
    "item": "minecraft:torch",
    "count": 4
  }}
}}
Shaped Summary:
{{
    "crafting_table": false,
    "materials": {{
        "minecraft:stick": 1,
        "minecraft:coals": 1,
    }}
}}
--- End of Document ---

Goals and Subgoals:
("goal"{tuple_delimiter}"mine log"{tuple_delimiter}"Punch or cut a tree to obtain logs."{tuple_delimiter}{{"None"}}{tuple_delimiter}"None"{tuple_delimiter}{{"logs": 1}}){record_delimiter}
("goal"{tuple_delimiter}"craft sticks"{tuple_delimiter}"Craft sticks, which are a basic crafting material."{tuple_delimiter}"None"{tuple_delimiter}{{"planks": 2}}{tuple_delimiter}{{"stick": 4}}){record_delimiter}
("goal"{tuple_delimiter}"craft a crafting table"{tuple_delimiter}"Craft a crafting table, which is used to craft more complex items."{tuple_delimiter}"None"{tuple_delimiter}{{"planks": 4}}{tuple_delimiter}{{"crafting_table": 1}}){record_delimiter}
("goal"{tuple_delimiter}"craft a torch"{tuple_delimiter}"Craft a torch that acts as a light source."{tuple_delimiter}"None"{tuple_delimiter}{{"stick": 1, "coals": 1}}{tuple_delimiter}{{"torch": 4}}){completion_delimiter}

######################
-Example 2-
######################
Document Text:
Obtaining
Breaking
Iron ore itself can be obtained by mining it with a stone pickaxe or higher enchanted with Silk Touch. When mined without Silk Touch, iron ore drops raw iron. It is affected by Fortune enchantment, dropping 1â€“2, 1â€“3, or 1â€“4 raw iron respectively with Fortune I, II, and III.

Usage
The primary usage of iron ore is to obtain iron ingots.
Smelting ingredient

--- Recipe ---
{{
  "type": "minecraft:smelting",
  "ingredient": {{
    "item": "minecraft:iron_ore"
  }},
  "result": "minecraft:iron_ingot",
  "experience": 0.7,
  "cookingtime": 200
}}
--- End of Document ---

Goals and Subgoals:
("goal"{tuple_delimiter}"mine iron ore"{tuple_delimiter}"Mine iron ore using a pickaxe, which is used to smelt iron ingots."{tuple_delimiter}{{"stone_pickaxe": 1}}{tuple_delimiter}"None"{tuple_delimiter}{{"iron_ore": 1}}){record_delimiter}
("goal"{tuple_delimiter}"smelt iron ingot"{tuple_delimiter}"Smelts iron ore into an iron ingot, which is a key material for crafting tools and weapons. Smelting requires a furnace and fuel such as coal or charcoal."{tuple_delimiter}{{"furnace": 1, "fuel": 1}}{tuple_delimiter}{{"iron_ore": 1}}{tuple_delimiter}{{"iron_ingot": 1}}){record_delimiter}
("subgoal"{tuple_delimiter}"smelt iron ingot"{tuple_delimiter}"mine iron ore"{tuple_delimiter}"Iron ore is smelted into iron ingots using a furnace"){completion_delimiter}

######################
-Example 3-
######################
Document Text:
Stone
For other uses, see Stone (disambiguation).
Stone is a block found underground in the Overworld or on the surface of mountains.

Obtaining
Stone requires a pickaxe to be mined, in which case it drops cobblestone. When mined without a pickaxe, it drops nothing. If a stone is mined with a Silk Touch enchanted pickaxe, it drops itself.
Times are for unenchanted tools as wielded by players with no status effects, measured in seconds. For more information, see Breaking Â§ Speed.
Natural generation
Stone makes up the majority of the solid blocks generated in the Overworld above y=0. From y=8 downwards, stone gradually transitions into deepslate, until it is completely replaced by deepslate at and below y=0.
When chunks generate, stone can be found under 1-5 layers of grass blocks, dirt, gravel, clay, coarse dirt, podzol, mycelium, sand, sandstone, red sand, red sandstone or terracotta, depending on the biome.
When the world is generating new chunks, some stone is replaced with blobs of other blocks. They may also be revealed on the side of small hills.
Stone also generates in igloo basements and some Overworld ruined portals.

--- Recipe ---
{{
    "type": "minecraft:smelting",
    "ingredient": {{
        "item": "minecraft:cobblestone"
    }},
    "result": "minecraft:stone",
    "experience": 0.1,
    "cookingtime": 200
}}
--- End of Document ---

Goals and Subgoals:
("goal"{tuple_delimiter}"mine cobblestone"{tuple_delimiter}"Mine cobblestone using a pickaxe, which is commonly found in the Overworld."{tuple_delimiter}{{"wooden_pickaxe": 1}}{tuple_delimiter}"None"{tuple_delimiter}{{"cobblestone": 1}}){record_delimiter}
("goal"{tuple_delimiter}"smelt stone"{tuple_delimiter}"Smelt cobblestone into stone."{tuple_delimiter}{{"furnace": 1}}{tuple_delimiter}{{"cobblestone": 1}}{tuple_delimiter}{{"stone": 1}}){record_delimiter}
("subgoal"{tuple_delimiter}"smelt stone"{tuple_delimiter}"mine cobblestone"{tuple_delimiter}"Mine cobblestone which can then be smelted into stone"{completion_delimiter}

######################
-Example 4-
######################
Document Text:
--- Recipe ---
{{
    "type": "minecraft:crafting_shaped",
    "pattern": [
        "XX",
        "X#",
        " #"
    ],
    "key": {{
        "#": {{
            "item": "minecraft:stick"
        }},
        "X": {{
            "tag": "minecraft:planks"
        }}
    }},
    "result": {{
        "item": "minecraft:wooden_axe"
    }}
}}
Shaped Summary:
{{
    "crafting_table": true,
    "materials": {{
        "minecraft:stick": 2,
        "minecraft:planks": 3,
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shaped",
    "pattern": [
        "XXX",
        " # ",
        " # "
    ],
    "key": {{
        "#": {{
            "item": "minecraft:stick"
        }},
        "X": {{
            "tag": "minecraft:stone_tool_materials"
        }}
    }},
    "result": {{
        "item": "minecraft:stone_pickaxe"
    }}
}}
Shaped Summary:
{{
    "crafting_table": true,
    "materials": {{
        "minecraft:stick": 2,
        "minecraft:stone_tool_materials": 3,
    }}
}}
--- Recipe ---
{{
  "type": "minecraft:crafting_shaped",
  "pattern": [
    "X",
    "X",
    "#"
  ],
  "key": {{
    "#": {{
      "item": "minecraft:stick"
    }},
    "X": {{
      "item": "minecraft:iron_ingot"
    }}
  }},
  "result": {{
    "item": "minecraft:iron_sword"
  }}
}}
Shaped Summary:
{{
    "crafting_table": true,
    "materials": {{
        "minecraft:stick": 1,
        "minecraft:iron_ingot": 2,
    }}
}}
--- End of Document ---

Goals and Subgoals:
("goal"{tuple_delimiter}"craft a wooden axe"{tuple_delimiter}"Crafts a wooden axe, which is used for chopping wood."{tuple_delimiter}{{"crafting_table": 1}}{tuple_delimiter}{{"stick": 2, "planks": 3}}{tuple_delimiter}{{"wooden_axe": 1}}){record_delimiter}
("goal"{tuple_delimiter}"craft a stone pickaxe"{tuple_delimiter}"Crafts a stone pickaxe. A pickaxe is used to mine ores."{tuple_delimiter}{{"crafting_table": 1}}{tuple_delimiter}{{"stick": 2, "stone_tool_materials": 3}}{tuple_delimiter}{{"stone_pickaxe": 1}}){record_delimiter}
("goal"{tuple_delimiter}"craft an iron sword"{tuple_delimiter}"Crafts a iron sword, which is used to fight monsters."{tuple_delimiter}{{"crafting_table": 1}}{tuple_delimiter}{{"stick": 1, "iron_ingot": 2}}{tuple_delimiter}{{"iron_sword": 1}}){completion_delimiter}

######################
-Example 5-
######################
Document Text:
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:acacia_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:acacia_planks",
        "count": 4
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:birch_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:birch_planks",
        "count": 4
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:jungle_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:jungle_planks",
        "count": 4
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:spruce_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:spruce_planks",
        "count": 4
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:oak_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:oak_planks",
        "count": 4
    }}
}}
--- Recipe ---
{{
    "type": "minecraft:crafting_shapeless",
    "group": "planks",
    "ingredients": [
        {{
            "tag": "minecraft:dark_oak_logs"
        }}
    ],
    "result": {{
        "item": "minecraft:dark_oak_planks",
        "count": 4
    }}
}}
--- End of Document ---

Goal and Subgoals:
("goal"{tuple_delimiter}"craft planks"{tuple_delimiter}"Craft planks, a basic crafting material"{tuple_delimiter}"None"{tuple_delimiter}{{"logs": 1}}{tuple_delimiter}{{"planks": 4}}){completion_delimiter}

######################
-Real Data-
######################
Document Text:
{input_text}
--- End of Document ---

Goals and Subgoals:
"""

PROMPTS["goal_merge"] = """You will be given a list of goals extracted from documents about the game Minecraft. Your job is to reduce the list by merging semantically equivalent goals by appropriately combining their properties, and by removing or editing malformed or incorrect goals. Each goal is structured as a tuple:
("goal",<goal_name>,<goal_description>,<goal_req_tools>,<goal_req_materials>,<goal_postconditions>)

Where the placeholders are defined as:
- goal_name: Name of the goal. Use short, specific names in the form of "<action> <minecraft_item>", such as "craft planks", "craft a wooden pickaxe", "mine cobblestone", or "smelt charcoal".
- goal_description: A concise explanation of what the goal entails.
- goal_req_tools: Needed tools to complete the goal, as a JSON object where keys are Minecraft tools and values are either "required" or "<minimum_tool_grade> or higher" (if there is a higher grade tool) for tools that have multiple grade levels, where <minimum_tool_grade> can be "none" if the goal can be achieved without the tool. Crafting tables and furnaces are considered as tools. Use "None" (as a string) if no tools are needed.
- goal_req_materials: Needed materials to complete the goal, as a JSON object where keys are Minecraft items and values are needed quantities of that item. If no materials are needed, set this to "None" (just as a standalone string, not as a JSON object or set or list).
- goal_postconditions: The resulting state or item after completing the goal, as a JSON object where the keys are Minecraft items and values are the quantity. If there are no post-conditions, set this to "None" (just as a standalone string, not as a JSON object or set or list).

Equivalent goals have the semantically the same names, purposes, required tools, required materials, and post-conditions. Goals that have different post-conditions (i.e. result in different items) should be kept separate, even if those items belong to a similar category or group. In other words, keep goals separate if they produce different outputs. Your reduced list should:
1. Contain all the unique goals from the original list, maintaining the properties of the original goal. Ensure that you only merge goals that are similar to one another. Include all other non-merged goals from the original list.
2. Merge equivalent goals by appropriately combining properties. Use short, specific names for <goal_name> in the form of "<action> <minecraft_item>", such as "craft planks", "craft a wooden pickaxe", "mine cobblestone", or "smelt charcoal". The level of detail in <goal_description> should be maintained.
3. Not contain more goals than the original list.
4. Not contain duplicate or equivalent goals.

List of goals:
{goal_list}

Reduce the given list of goals as instructed, and return ONLY the updated list in the same format (do not put square brackets around the list). If no changes to the list are needed, then just return the original list. Do not generate any explanation, introduction, or other extra text.
"""

PROMPTS["subgoal_merge_and_expand"] = """You will be given a list of goals and a list of relationships between goals and subgoals from the first list, both extracted from documents about the game Minecraft.

Your task is to refine the list of relationships by:
1. Completing Missing Relationships. Based on the goal list, infer and add any missing goal-subgoal relationships that are logically implied but not present in the original relationship list. For every goal, establish subgoal relationships for each required material and tool that must be obtained or crafted defined in the goal tuples. The goals within the relationships must exist in the goal list.
2. Merging Equivalent Relationships. If multiple relationships exist with the same "goal_name" and "subgoal_name", merge them into a single relationship by combining or summarizing the "relationship_description".
3. Removing Indirect Relationships. Remove any indirect relationships where the goal does not directly decompose into the subgoal. Do not include relationships between goals and subsubgoals, instead this should be two relationships: one between the goal and subgoal, and one between the subgoal and subsubgoal. For example, mining cobblestone does not need sticks, but needs a pickaxe which needs stick. Therefore, the relationship between mining cobblestone and crafting sticks can be excluded.
4. Normalizing Goal and Subgoal Names. Ensure all goal_name and subgoal_name values in the relationships match exactly with the goal_name values from the given list of goals. If needed, rename the values in the relationships to match the goal names from the provided list.

Each goal in the list of goals is structured as a tuple:
("goal",<goal_name>,<goal_description>,<goal_req_tools>,<goal_req_materials>,<goal_postconditions>)

Where the placeholders are defined as:
- goal_name: Name of the goal.
- goal_description: A concise explanation of what the goal entails.
- goal_req_tools: Needed tools to complete the goal, as a JSON object where keys are Minecraft tools and values are either "required" or "<minimum_tool_grade> or higher" (if there is a higher grade tool), where <minimum_tool_grade> can be "none" if the goal can be achieved without the tool. Use "None" (as a string) if no tools are needed.
- goal_req_materials: Needed materials to complete the goal, as a JSON object where keys are Minecraft items and values are needed quantities of that item. Use "None" (as a string) if no materials are needed.
- goal_postconditions: The resulting state or item after completing the goal, as a JSON object where the keys are Minecraft items and values are the quantity.

Each relationship is structured as a tuple:
("subgoal",<goal_name>,<subgoal_name>,<relationship_description>) 

Where the placeholders are defined as:
- goal_name: Name of the higher-level goal, which must exist in the given list of goals.
- subgoal_name: Name of the subgoal, which must exist in the given list of goals.
- relationship_description: Explanation as to how and why the source goal and the subgoal are related to each other.

List of goals:
{goal_list}

List of relationships:
{subgoal_list}

Refine the given list of relationships as instructed using the given list of goals, and return ONLY the updated list in the same format (do not put square brackets around the list). Do not generate any explanation, introduction, or extra text.
"""

PROMPTS["goal_inference"] = """You are a MineCraft game expert and you can guide agents to complete complex tasks. For a given game screen, task, and context information, you need to complete "goal inference" and "visual inference".
The context information is a set of possible goals to choose from for "goal inference".
"goal inference": According to the task, you need to select the goal from given options that best matches the given query.
"visual inference": According to the game screen, you need to infer the following aspects: health bar, food bar, hotbar, environment.

[Example 1]
<task>: make a stone sword
<context>:
Option 1:
{{
    "name": "craft a stone pickaxe",
    "description": "Crafts a stone pickaxe, which is more durable than a wooden pickaxe and can be used to mine iron ore.",
    "postconditions": {{"stone_pickaxe": 1}}
}}

Option 2:
{{
    "name": "craft a wooden sword",
    "description": "Crafts a wooden sword, which has 4 attack damage and has a durability of 59. A sword is a melee weapon that is mainly used to damage entities and for cutting cobwebs or bamboo.",
    "postconditions": {{"wooden_sword": 1}}
}}

Option 3:
{{
    "name": "craft a stone sword",
    "description": "Crafts a stone sword, which has 5 attack damage and has a durability of 131. A sword is a melee weapon that is mainly used to damage entities and for cutting cobwebs or bamboo.",
    "postconditions": {{"stone_sword": 1}}
}}

Output:
{{
    "goal inference": "craft a stone sword",
    "visual inference": {{
        "health bar": "full",
        "food bar": "full",
        "hotbar": "empty",
        "environment": "forest"
    }}
}}

[Example 2]
<task>: create an iron pickaxe
<context>:
Option 1:
{{
    "name": "craft an iron sword",
    "description": "Crafts an iron sword, which is a weapon that can be used to fight and damage vairous entities.",
    "postconditions": {{"iron_sword": 1}}
}}

Option 2:
{{
    "name": "craft an iron pickaxe",
    "description": "Crafts an iron pickaxe, which is more durable than a stone pickaxe and can be used to mine various materials.",
    "postconditions": {{"iron_pickaxe": 1}}
}}

Option 3:
{{
    "name": "craft a stone pickaxe",
    "description": "Crafts a stone pickaxe, which is more durable than a wooden pickaxe and can be used to mine iron ore.",
    "postconditions": {{"stone_pickaxe": 1}}
}}

Output:
{{
    "goal inference": "craft an iron pickaxe",
    "visual inference": {{
        "health bar": "full",
        "food bar": "full",
        "hotbar": "empty",
        "environment": "desert"
    }}
}}

Here is a game screen and task, you MUST respond in JSON format as shown in the example outputs WITHOUT further explanation, introduction, or extra text. Complete "goal inference" by setting it to the value of the "name" of the option that best matches the given task as shown in the example. Other fields should be completed based on the given game screen.

<task>: {task}
<context>:
{context}

Output:
"""

PROMPTS["planning_example"] = """<goal>
craft an iron sword

<visual info>
health bar: full
food bar: full
hotbar: empty
environment: forest

<goal hierarchy>
{
    "craft an iron sword": {
        "description": "Craft an iron sword, which is used as a melee weapon.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 1,
            "iron_ingot": 2
        },
        "postconditions": {
            "iron_sword": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft an iron sword"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft an iron sword"
            },
            {
                "subgoal": "smelt iron ingot",
                "relationship_description": "smelt iron ingot is used by craft an iron sword"
            }
        ]
    },
    "craft a crafting table": {
        "description": "Craft a crafting table, which is used to craft more complex items.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 4
        },
        "postconditions": {
            "crafting_table": 1
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a crafting table"
            }
        ]
    },
    "craft planks": {
        "description": "Craft planks, a basic crafting material.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "logs": 1
        },
        "postconditions": {
            "planks": 4
        },
        "subgoals": [
            {
                "subgoal": "mine log",
                "relationship_description": "mine log is used by craft planks"
            }
        ]
    },
    "mine log": {
        "description": "Punch or cut a tree to obtain logs.",
        "aliases": [],
        "tools": "None",
        "materials": "None",
        "postconditions": {
            "logs": 1
        },
        "subgoals": []
    },
    "craft sticks": {
        "description": "Craft sticks, which are a basic crafting material.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 2
        },
        "postconditions": {
            "stick": 4
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft sticks"
            }
        ]
    },
    "smelt iron ingot": {
        "description": "Smelt raw iron into an iron ingot, which is a key material for crafting tools and weapons. Smelting requires a furnace and fuel.",
        "aliases": [],
        "tools": {
            "furnace": 1,
            "fuel": 1
        },
        "materials": {
            "iron_ore": 1
        },
        "postconditions": {
            "iron_ingot": 1
        },
        "subgoals": [
            {
                "subgoal": "mine iron ore",
                "relationship_description": "Iron ore is mined to be smelted into iron ingots"
            },
            {
                "subgoal": "craft a furnace",
                "relationship_description": "craft a furnace is used by smelt iron ingot"
            }
        ]
    },
    "mine iron ore": {
        "description": "Mine iron ore using a stone pickaxe or higher to obtain raw iron.",
        "aliases": [],
        "tools": {
            "stone_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "iron_ore": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a stone pickaxe",
                "relationship_description": "craft a stone pickaxe is used by mine iron ore"
            }
        ]
    },
    "craft a stone pickaxe": {
        "description": "Craft a stone pickaxe, which is more durable than a wooden pickaxe.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "cobblestone": 3
        },
        "postconditions": {
            "stone_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a stone pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a stone pickaxe"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a stone pickaxe"
            }
        ]
    },
    "mine cobblestone": {
        "description": "Mine cobblestone using a pickaxe, which is commonly found in the Overworld.",
        "aliases": [],
        "tools": {
            "wooden_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "cobblestone": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a wooden pickaxe",
                "relationship_description": "craft a wooden pickaxe is used by mine cobblestone"
            }
        ]
    },
    "craft a wooden pickaxe": {
        "description": "Craft a wooden pickaxe, which is the most basic pickaxe for mining.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "planks": 3
        },
        "postconditions": {
            "wooden_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a wooden pickaxe"
            }
        ]
    },
    "craft a furnace": {
        "description": "Craft a furnace, which is used for smelting items.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "cobblestone": 8
        },
        "postconditions": {
            "furnace": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a furnace"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a furnace"
            }
        ]
    }
}

<materials and tools>
1. logs: 4
2. planks: 12
3. stick: 8
4. crafting_table: 1
5. wooden_pickaxe: 1
6. cobblestone: 11
7. stone_pickaxe: 1
8. iron_ore: 2
9. furnace: 1
10. iron_ingot: 2
11. iron_sword: 1

<planning>
{
  "step 1": {"task": "chop a tree", "goal": ["logs", 4]},
  "step 2": {"task": "craft planks", "goal": ["planks", 12]},
  "step 3": {"task": "craft stick", "goal": ["stick", 8]},
  "step 4": {"task": "craft crafting table", "goal": ["crafting_table", 1]},
  "step 5": {"task": "craft wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 6": {"task": "equip wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 7": {"task": "dig down and break down cobblestone", "goal": ["cobblestone", 11]},
  "step 8": {"task": "craft stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 9": {"task": "equip stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 10": {"task": "dig down and break down iron ore", "goal": ["iron_ore", 2]},
  "step 11": {"task": "craft a furnace", "goal": ["furnace", 1]},
  "step 12": {"task": "smelt iron ingot", "goal": ["iron_ingot", 2]},
  "step 13": {"task": "craft iron sword", "goal": ["iron_sword", 1]}
}
"""

PROMPTS["planning"] = """You are a MineCraft game expert and you can guide agents to complete complex tasks. For a given overall goal, game screen, hierarchy of goals, and list of needed materials, construct a ordered plan that completes the given task. The goal hierarchy is structured as a JSON object whose keys are names of goals, and values are information about the goal and its and subgoals. You will be given a list of tools and materials and amounts needed for you to obtain and craft to complete the overall goal. Based on the information from the goal hierarchy and the list of tools and materials, create a plan in JSON format as shown in the following example:

######################
-Example-
######################
{example}
######################

######################
-Real Task-
######################
<goal>
{goal}

<visual info>
{visual_info}

<goal hierarchy>
{goal_hierarchy}

<materials and tools>
{materials_and_tools}

<planning>

Complete <planning> for the given overall <goal> with valid JSON as instructed and in the format shown in the example. Use the information in the goal hierarchy, game screen, and list of tools and materials and their amounts to generate "task" and "goal" in each step of the plan. Use the same wording styles and patterns for the "task" in each step as shown in the example plan. Only output the plan as a valid JSON object with no additional text, introduction, or explanation. Do not use Markdown.
"""

PROMPTS["planning_no_hierarchy_or_list_prompt"] = """You are a MineCraft game expert and you can guide agents to complete complex tasks. For a given overall goal and game screen, construct a ordered plan that completes the given task. Create a plan in JSON format as shown in the following example:

######################
-Example-
######################
{example}
######################

######################
-Real Task-
######################

<goal>
{goal}

<visual info>
{visual_info}

<planning>

Complete <planning> for the given overall <goal> with valid JSON as instructed and in the format shown in the example. Use the same wording styles and patterns for the "task" in each step as shown in the example plan. Only output the plan as a valid JSON object with no additional text, introduction, or explanation. Do not use Markdown.
"""


PROMPTS["planning_with_mat_list_prompt"] = """You are a MineCraft game expert and you can guide agents to complete complex tasks. For a given overall goal, game screen, and list of needed materials, construct a ordered plan that completes the given task. You will be given a list of tools and materials and amounts needed for you to obtain and craft to complete the overall goal. Based on the information from the list of tools and materials, create a plan in JSON format as shown in the following example:

######################
-Example-
######################
{example}
######################

######################
-Real Task-
######################

<goal>
{goal}

<visual info>
{visual_info}

<materials and tools>
{materials_and_tools}

<planning>

Complete <planning> for the given overall <goal> with valid JSON as instructed and in the format shown in the example. Use the information in the game screen and list of tools and materials and their amounts to generate "task" and "goal" in each step of the plan. Use the same wording styles and patterns for the "task" in each step as shown in the example plan. Only output the plan as a valid JSON object with no additional text, introduction, or explanation. Do not use Markdown.
"""

PROMPTS["planning_with_hierarchy_prompt"] = """You are a MineCraft game expert and you can guide agents to complete complex tasks. For a given overall goal, game screen, and hierarchy of goals, construct a ordered plan that completes the given task. The goal hierarchy is structured as a JSON object whose keys are names of goals, and values are information about the goal and its and subgoals. Based on the information from the goal hierarchy and the list of tools and materials, create a plan in JSON format as shown in the following example:

######################
-Example-
######################
{example}
######################

######################
-Real Task-
######################

<goal>
{goal}

<visual info>
{visual_info}

<goal hierarchy>
{goal_hierarchy}

<planning>

Complete <planning> for the given overall <goal> with valid JSON as instructed and in the format shown in the example. Use the information in the goal hierarchy and game screen to generate "task" and "goal" in each step of the plan. Use the same wording styles and patterns for the "task" in each step as shown in the example plan. Only output the plan as a valid JSON object with no additional text, introduction, or explanation. Do not use Markdown.
"""

PROMPTS["replan"] = """
You are a MineCraft game expert and you can guide agents to complete complex tasks. 
Agent is executing the <task>: {task}, and agent meets <error>: {error}.
Based on the given <error> information, perform replanning to allow the agent to successfully complete the <task> with the help of the provided <crafting summaries>.

You MUST focus on how to solve the <error>.

I will give you an example as follows:
[Example]
<crafting summaries>:
craft 1 crafting_table summary:
1. log: 1
2. planks: 4
3. crafting_table: 1

<task>: craft wooden_pickaxe.
<error>: missing material: {{"crafting_table": 1}}.
<replan>: 
{{
    "step 1": {{"task": "chop tree", "goal": ["logs", 1]}},
    "step 2": {{"task": "craft planks", "goal": ["planks", 4]}},
    "step 3": {{"task": "craft crafting table", "goal": ["crafting_table", 1]}}
}}

Here is a game screen and task, you MUST output in example format. Remember <task planning> MUST output in example format, and your response must ONLY contain the task planning information in JSON format such that the execution of your plan completes the given task, WITHOUT further explanation or extra text.
<crafting summaries>:
{summaries}
<task>: {task}
<error>: {error}

Respond only with valid JSON. Do not write an introduction, explanation, or summary.
<replan>:
"""

PROMPTS["gog_planning_example_no_desc"] = """<goal>
craft an iron sword

<visual info>
health bar: full
food bar: full
hotbar: empty
environment: forest

<goal hierarchy>
{
    "craft an iron sword": {
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 1,
            "iron_ingot": 2
        },
        "postconditions": {
            "iron_sword": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft an iron sword"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft an iron sword"
            },
            {
                "subgoal": "smelt iron ingot",
                "relationship_description": "smelt iron ingot is used by craft an iron sword"
            }
        ]
    },
    "craft a crafting table": {
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 4
        },
        "postconditions": {
            "crafting_table": 1
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a crafting table"
            }
        ]
    },
    "craft planks": {
        "aliases": [],
        "tools": "None",
        "materials": {
            "logs": 1
        },
        "postconditions": {
            "planks": 4
        },
        "subgoals": [
            {
                "subgoal": "mine log",
                "relationship_description": "mine log is used by craft planks"
            }
        ]
    },
    "mine log": {
        "aliases": [],
        "tools": "None",
        "materials": "None",
        "postconditions": {
            "logs": 1
        },
        "subgoals": []
    },
    "craft sticks": {
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 2
        },
        "postconditions": {
            "stick": 4
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft sticks"
            }
        ]
    },
    "smelt iron ingot": {
        "aliases": [],
        "tools": {
            "furnace": 1,
            "fuel": 1
        },
        "materials": {
            "iron_ore": 1
        },
        "postconditions": {
            "iron_ingot": 1
        },
        "subgoals": [
            {
                "subgoal": "mine iron ore",
                "relationship_description": "Iron ore is mined to be smelted into iron ingots"
            },
            {
                "subgoal": "craft a furnace",
                "relationship_description": "craft a furnace is used by smelt iron ingot"
            }
        ]
    },
    "mine iron ore": {
        "aliases": [],
        "tools": {
            "stone_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "iron_ore": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a stone pickaxe",
                "relationship_description": "craft a stone pickaxe is used by mine iron ore"
            }
        ]
    },
    "craft a stone pickaxe": {
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "cobblestone": 3
        },
        "postconditions": {
            "stone_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a stone pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a stone pickaxe"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a stone pickaxe"
            }
        ]
    },
    "mine cobblestone": {
        "aliases": [],
        "tools": {
            "wooden_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "cobblestone": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a wooden pickaxe",
                "relationship_description": "craft a wooden pickaxe is used by mine cobblestone"
            }
        ]
    },
    "craft a wooden pickaxe": {
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "planks": 3
        },
        "postconditions": {
            "wooden_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a wooden pickaxe"
            }
        ]
    },
    "craft a furnace": {
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "cobblestone": 8
        },
        "postconditions": {
            "furnace": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a furnace"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a furnace"
            }
        ]
    }
}

<materials and tools>
1. logs: 4
2. planks: 12
3. stick: 8
4. crafting_table: 1
5. wooden_pickaxe: 1
6. cobblestone: 11
7. stone_pickaxe: 1
8. iron_ore: 2
9. furnace: 1
10. iron_ingot: 2
11. iron_sword: 1

<planning>
{
  "step 1": {"task": "chop a tree", "goal": ["logs", 4]},
  "step 2": {"task": "craft planks", "goal": ["planks", 12]},
  "step 3": {"task": "craft stick", "goal": ["stick", 8]},
  "step 4": {"task": "craft crafting table", "goal": ["crafting_table", 1]},
  "step 5": {"task": "craft wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 6": {"task": "equip wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 7": {"task": "dig down and break down cobblestone", "goal": ["cobblestone", 11]},
  "step 8": {"task": "craft stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 9": {"task": "equip stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 10": {"task": "dig down and break down iron ore", "goal": ["iron_ore", 2]},
  "step 11": {"task": "craft a furnace", "goal": ["furnace", 1]},
  "step 12": {"task": "smelt iron ingot", "goal": ["iron_ingot", 2]},
  "step 13": {"task": "craft iron sword", "goal": ["iron_sword", 1]}
}
"""

PROMPTS["planning_example_with_hierarchy"] = """<goal>
craft an iron sword

<visual info>
health bar: full
food bar: full
hotbar: empty
environment: forest

<goal hierarchy>
{
    "craft an iron sword": {
        "description": "Craft an iron sword, which is used as a melee weapon.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 1,
            "iron_ingot": 2
        },
        "postconditions": {
            "iron_sword": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft an iron sword"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft an iron sword"
            },
            {
                "subgoal": "smelt iron ingot",
                "relationship_description": "smelt iron ingot is used by craft an iron sword"
            }
        ]
    },
    "craft a crafting table": {
        "description": "Craft a crafting table, which is used to craft more complex items.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 4
        },
        "postconditions": {
            "crafting_table": 1
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a crafting table"
            }
        ]
    },
    "craft planks": {
        "description": "Craft planks, a basic crafting material.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "logs": 1
        },
        "postconditions": {
            "planks": 4
        },
        "subgoals": [
            {
                "subgoal": "mine log",
                "relationship_description": "mine log is used by craft planks"
            }
        ]
    },
    "mine log": {
        "description": "Punch or cut a tree to obtain logs.",
        "aliases": [],
        "tools": "None",
        "materials": "None",
        "postconditions": {
            "logs": 1
        },
        "subgoals": []
    },
    "craft sticks": {
        "description": "Craft sticks, which are a basic crafting material.",
        "aliases": [],
        "tools": "None",
        "materials": {
            "planks": 2
        },
        "postconditions": {
            "stick": 4
        },
        "subgoals": [
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft sticks"
            }
        ]
    },
    "smelt iron ingot": {
        "description": "Smelt raw iron into an iron ingot, which is a key material for crafting tools and weapons. Smelting requires a furnace and fuel.",
        "aliases": [],
        "tools": {
            "furnace": 1,
            "fuel": 1
        },
        "materials": {
            "iron_ore": 1
        },
        "postconditions": {
            "iron_ingot": 1
        },
        "subgoals": [
            {
                "subgoal": "mine iron ore",
                "relationship_description": "Iron ore is mined to be smelted into iron ingots"
            },
            {
                "subgoal": "craft a furnace",
                "relationship_description": "craft a furnace is used by smelt iron ingot"
            }
        ]
    },
    "mine iron ore": {
        "description": "Mine iron ore using a stone pickaxe or higher to obtain raw iron.",
        "aliases": [],
        "tools": {
            "stone_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "iron_ore": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a stone pickaxe",
                "relationship_description": "craft a stone pickaxe is used by mine iron ore"
            }
        ]
    },
    "craft a stone pickaxe": {
        "description": "Craft a stone pickaxe, which is more durable than a wooden pickaxe.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "cobblestone": 3
        },
        "postconditions": {
            "stone_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a stone pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a stone pickaxe"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a stone pickaxe"
            }
        ]
    },
    "mine cobblestone": {
        "description": "Mine cobblestone using a pickaxe, which is commonly found in the Overworld.",
        "aliases": [],
        "tools": {
            "wooden_pickaxe": 1
        },
        "materials": "None",
        "postconditions": {
            "cobblestone": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a wooden pickaxe",
                "relationship_description": "craft a wooden pickaxe is used by mine cobblestone"
            }
        ]
    },
    "craft a wooden pickaxe": {
        "description": "Craft a wooden pickaxe, which is the most basic pickaxe for mining.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "stick": 2,
            "planks": 3
        },
        "postconditions": {
            "wooden_pickaxe": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft sticks",
                "relationship_description": "craft sticks is used by craft a wooden pickaxe"
            },
            {
                "subgoal": "craft planks",
                "relationship_description": "craft planks is used by craft a wooden pickaxe"
            }
        ]
    },
    "craft a furnace": {
        "description": "Craft a furnace, which is used for smelting items.",
        "aliases": [],
        "tools": {
            "crafting_table": 1
        },
        "materials": {
            "cobblestone": 8
        },
        "postconditions": {
            "furnace": 1
        },
        "subgoals": [
            {
                "subgoal": "craft a crafting table",
                "relationship_description": "craft a crafting table is used by craft a furnace"
            },
            {
                "subgoal": "mine cobblestone",
                "relationship_description": "mine cobblestone is used by craft a furnace"
            }
        ]
    }
}

<planning>
{
  "step 1": {"task": "chop a tree", "goal": ["logs", 4]},
  "step 2": {"task": "craft planks", "goal": ["planks", 12]},
  "step 3": {"task": "craft stick", "goal": ["stick", 8]},
  "step 4": {"task": "craft crafting table", "goal": ["crafting_table", 1]},
  "step 5": {"task": "craft wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 6": {"task": "equip wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 7": {"task": "dig down and break down cobblestone", "goal": ["cobblestone", 11]},
  "step 8": {"task": "craft stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 9": {"task": "equip stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 10": {"task": "dig down and break down iron ore", "goal": ["iron_ore", 2]},
  "step 11": {"task": "craft a furnace", "goal": ["furnace", 1]},
  "step 12": {"task": "smelt iron ingot", "goal": ["iron_ingot", 2]},
  "step 13": {"task": "craft iron sword", "goal": ["iron_sword", 1]}
}
"""

PROMPTS["planning_example_with_mat_list"] = """<goal>
craft an iron sword

<visual info>
health bar: full
food bar: full
hotbar: empty
environment: forest

<materials and tools>
1. logs: 4
2. planks: 12
3. stick: 8
4. crafting_table: 1
5. wooden_pickaxe: 1
6. cobblestone: 11
7. stone_pickaxe: 1
8. iron_ore: 2
9. furnace: 1
10. iron_ingot: 2
11. iron_sword: 1

<planning>
{
  "step 1": {"task": "chop a tree", "goal": ["logs", 4]},
  "step 2": {"task": "craft planks", "goal": ["planks", 12]},
  "step 3": {"task": "craft stick", "goal": ["stick", 8]},
  "step 4": {"task": "craft crafting table", "goal": ["crafting_table", 1]},
  "step 5": {"task": "craft wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 6": {"task": "equip wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 7": {"task": "dig down and break down cobblestone", "goal": ["cobblestone", 11]},
  "step 8": {"task": "craft stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 9": {"task": "equip stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 10": {"task": "dig down and break down iron ore", "goal": ["iron_ore", 2]},
  "step 11": {"task": "craft a furnace", "goal": ["furnace", 1]},
  "step 12": {"task": "smelt iron ingot", "goal": ["iron_ingot", 2]},
  "step 13": {"task": "craft iron sword", "goal": ["iron_sword", 1]}
}
"""

PROMPTS["planning_example_no_hierarchy_or_list"] = """<goal>
craft an iron sword

<visual info>
health bar: full
food bar: full
hotbar: empty
environment: forest

<planning>
{
  "step 1": {"task": "chop a tree", "goal": ["logs", 4]},
  "step 2": {"task": "craft planks", "goal": ["planks", 12]},
  "step 3": {"task": "craft stick", "goal": ["stick", 8]},
  "step 4": {"task": "craft crafting table", "goal": ["crafting_table", 1]},
  "step 5": {"task": "craft wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 6": {"task": "equip wooden pickaxe", "goal": ["wooden_pickaxe", 1]},
  "step 7": {"task": "dig down and break down cobblestone", "goal": ["cobblestone", 11]},
  "step 8": {"task": "craft stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 9": {"task": "equip stone pickaxe", "goal": ["stone_pickaxe", 1]},
  "step 10": {"task": "dig down and break down iron ore", "goal": ["iron_ore", 2]},
  "step 11": {"task": "craft a furnace", "goal": ["furnace", 1]},
  "step 12": {"task": "smelt iron ingot", "goal": ["iron_ingot", 2]},
  "step 13": {"task": "craft iron sword", "goal": ["iron_sword", 1]}
}
"""