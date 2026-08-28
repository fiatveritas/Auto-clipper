"""
Dataset annotation schema.

Primary events answer:

    "What happened?"

Tags answer:

    "What describes the primary event?"
"""

PRIMARY_EVENTS = [
    "Kill",
    "Death",
    "Objective",
    "Structure",
    "Teamfight",
    "Escape",
    "Other",
    "Not Relevant",
]

TAG_GROUPS = {

    "Kill": [
        "Double Kill",
        "Triple Kill",
        "Quadra Kill",
        "Pentakill",
        "Ace",
    ],

    "Death": [

    ],

    "Objective": [
        "Dragon",
        "Elder Dragon",
        "Baron Nashor",
        "Rift Herald",
        "Void Grubs",
        "Atakhan",
        "Steal",
    ],

    "Structure": [
        "Tower",
        "Inhibitor",
        "Nexus",
        "Game Ending",
    ],

    "Teamfight": [

    ],

    "Escape": [

    ],

    "Other": [

    ],

    "Not Relevant": [
        "N/A"
    ]
}

# Flat list used by DatasetManager validation
TAGS = sorted({
    tag
    for tags in TAG_GROUPS.values()
    for tag in tags
})