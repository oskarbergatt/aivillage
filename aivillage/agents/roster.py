"""The villagers: eight founders, four later arrivals, four resource workers
and three children."""
from __future__ import annotations

from .persona import Look, Persona, Voice

DAY = [(6.5, 7.5, "meal"), (7.5, 12.0, "work"), (12.0, 13.0, "meal"),
       (13.0, 17.0, "work"), (17.0, 18.5, "free"), (18.5, 19.5, "meal"),
       (19.5, 22.0, "free"), (22.0, 30.0, "sleep")]

NIGHT = [(0.0, 1.0, "free"), (1.0, 8.0, "sleep"), (8.0, 16.0, "sleep"),
         (16.0, 19.0, "free"), (19.0, 23.0, "work"), (23.0, 24.0, "free")]

# Children do not hold a trade.  Lessons in the morning, the square in the
# afternoon, and an early bedtime.
KID = [(7.0, 8.0, "meal"), (8.0, 12.5, "school"), (12.5, 13.5, "meal"),
       (13.5, 17.5, "play"), (17.5, 19.0, "free"), (19.0, 20.0, "meal"),
       (20.0, 21.5, "free"), (21.5, 30.0, "sleep")]


ROSTER: list[Persona] = [
    Persona(
        key="marrow", name="Marrow Vane", job="blacksmith", home="marrow",
        work="workshop",
        look=Look(skin=2, hair=0, cloth=0, hair_style="wild", hat="", version=0,
                  apron=True, beard=True),
        traits={"curiosity": 0.40, "sociability": 0.35, "diligence": 0.85,
                "grumpiness": 0.75, "creativity": 0.45},
        bio=("The village smith. Broad hands, blunt tongue, and an unreasonable "
             "affection for his anvil, which he calls 'the old girl'. He has "
             "been here longer than the well and will tell you so."),
        quirk="pretends not to care, then quietly fixes everyone's tools for free",
        voice=Voice(rate=150, volume=0.95, hint="david"),
        schedule=DAY,
    ),
    Persona(
        key="pip", name="Pip Hollow", job="farmer", home="pip", work="farm",
        look=Look(skin=0, hair=2, cloth=3, hair_style="bun", hat="straw", version=1,
                  apron=True),
        traits={"curiosity": 0.70, "sociability": 0.85, "diligence": 0.65,
                "grumpiness": 0.15, "creativity": 0.55},
        bio=("Grows almost everything the village eats and cannot stop talking "
             "about turnips. Believes every problem is solvable with compost "
             "and enthusiasm, usually in that order."),
        quirk="names individual vegetables and remembers them fondly",
        voice=Voice(rate=195, volume=0.95, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="sable", name="Sable Quill", job="artist", home="sable", work="home_sable",
        look=Look(skin=1, hair=4, cloth=2, hair_style="long", hat="", version=2),
        traits={"curiosity": 0.95, "sociability": 0.50, "diligence": 0.40,
                "grumpiness": 0.30, "creativity": 0.95},
        bio=("Paints the village and everyone in it, usually badly and always "
             "dramatically. Speaks in metaphors and takes offence at good light "
             "going to waste."),
        quirk="describes ordinary weather as if it were a personal betrayal",
        voice=Voice(rate=145, volume=0.7, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="orin", name="Orin Bell", job="baker", home="orin", work="home_orin",
        look=Look(skin=0, hair=2, cloth=4, hair_style="short", hat="cap", version=3,
                  apron=True),
        traits={"curiosity": 0.60, "sociability": 0.95, "diligence": 0.75,
                "grumpiness": 0.15, "creativity": 0.50},
        bio=("Runs the bakery, the rumour mill and, unofficially, the village. "
             "Feeds people first and asks questions immediately afterwards."),
        quirk="knows everyone's business and shares it with genuine warmth",
        voice=Voice(rate=175, volume=0.9, hint="mark"),
        schedule=DAY,
    ),
    Persona(
        key="hazel", name="Hazel Reed", job="herbalist", home="hazel",
        work="woods_west",
        look=Look(skin=3, hair=5, cloth=5, hair_style="long", hat="hood", version=4),
        traits={"curiosity": 0.85, "sociability": 0.45, "diligence": 0.60,
                "grumpiness": 0.35, "creativity": 0.70},
        bio=("Knows which mushroom will cure you and which will do the opposite. "
             "Answers questions with better questions. Has never once been seen "
             "hurrying."),
        quirk="speaks in riddles when a straight answer would do",
        voice=Voice(rate=140, volume=0.75, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="bram", name="Bram Tock", job="builder", home="bram", work="buildsite",
        look=Look(skin=1, hair=1, cloth=6, hair_style="short", hat="cap", version=5,
                  beard=True),
        traits={"curiosity": 0.50, "sociability": 0.55, "diligence": 0.95,
                "grumpiness": 0.55, "creativity": 0.45},
        bio=("Building the town hall, and he will finish it, weather and "
             "interruptions permitting. Measures twice, complains once, builds "
             "once."),
        quirk="can tell you the exact measurements of any doorway in the village",
        voice=Voice(rate=160, volume=0.9, hint="david"),
        schedule=DAY,
    ),
    Persona(
        key="nim", name="Nim Farrow", job="fisher", home="nim", work="pond",
        look=Look(skin=4, hair=0, cloth=7, hair_style="wild", hat="straw", version=6),
        traits={"curiosity": 0.60, "sociability": 0.40, "diligence": 0.65,
                "grumpiness": 0.50, "creativity": 0.40},
        bio=("Fishes the pond, though everyone suspects the pond has never held "
             "much. Superstitious about gulls. Comfortable with long silences."),
        quirk="treats every catch, however small, as a personal achievement",
        voice=Voice(rate=150, volume=0.7, hint="david"),
        schedule=DAY,
    ),
    Persona(
        key="wisp", name="Wisp", job="forager", home="wisp", work="woods_east",
        look=Look(skin=0, hair=4, cloth=7, hair_style="wild", hat="hood", version=7),
        traits={"curiosity": 0.90, "sociability": 0.30, "diligence": 0.50,
                "grumpiness": 0.60, "creativity": 0.85},
        bio=("No one is entirely sure when Wisp arrived or where they sleep. "
             "They forage at night, speak in half-finished poems, and know every "
             "path through the woods."),
        quirk="refers to themself in the third person when tired",
        voice=Voice(rate=130, volume=0.6, hint="zira"),
        schedule=NIGHT, nocturnal=True,
    ),
    # -- v0.3 adults -----------------------------------------------------
    Persona(
        key="june", name="June Thistle", job="teacher", home="june",
        work="school", age=34,
        look=Look(skin=1, hair=3, cloth=1, hair_style="bun", hat="", version=8),
        traits={"curiosity": 0.90, "sociability": 0.75, "diligence": 0.70,
                "grumpiness": 0.20, "creativity": 0.70},
        bio=("Keeps the village school in the shade of the bell post. She can "
             "make a lesson out of a beetle, a bread crust or an argument. "
             "Believes every child is one good question away from paying attention."),
        quirk="answers a question with a question, then answers it herself",
        voice=Voice(rate=185, volume=0.85, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="fen", name="Fen Barrow", job="miller", home="fen", work="mill",
        age=41,
        look=Look(skin=2, hair=1, cloth=3, hair_style="short", hat="cap",
                  version=9, apron=True, beard=True),
        traits={"curiosity": 0.45, "sociability": 0.50, "diligence": 0.90,
                "grumpiness": 0.40, "creativity": 0.30},
        bio=("Runs the mill and the flour dust that comes with it. Counts sacks "
             "twice and people once. The wind is the only thing he truly trusts."),
        quirk="gives the weather a fair hearing before blaming it",
        voice=Voice(rate=155, volume=0.9, hint="david"),
        schedule=DAY,
    ),
    Persona(
        key="mira", name="Mira Loom", job="weaver", home="mira", work="home_mira",
        age=29,
        look=Look(skin=3, hair=5, cloth=2, hair_style="long", hat="", version=10),
        traits={"curiosity": 0.65, "sociability": 0.55, "diligence": 0.80,
                "grumpiness": 0.25, "creativity": 0.90},
        bio=("Weaves cloth, gossip and occasionally a little weather into her "
             "patterns. Her loom is the loudest thing in the village and she "
             "will not apologise for it."),
        quirk="describes people by the colour she would weave them in",
        voice=Voice(rate=165, volume=0.8, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="tobin", name="Tobin Rusk", job="tinker", home="tobin", work="workshop",
        age=52,
        look=Look(skin=4, hair=4, cloth=6, hair_style="wild", hat="", version=11,
                  beard=True),
        traits={"curiosity": 0.80, "sociability": 0.60, "diligence": 0.60,
                "grumpiness": 0.45, "creativity": 0.75},
        bio=("Fixes what other people have given up on: pots, hinges, kettles, "
             "occasionally an argument. Carries three useful things and eleven "
             "useless ones at all times."),
        quirk="cannot pass a broken object without turning it over",
        voice=Voice(rate=170, volume=0.85, hint="mark"),
        schedule=DAY,
    ),
    # -- v0.4 resource trades --------------------------------------------
    Persona(
        key="maude", name="Maude Ash", job="shepherd", home="maude",
        work="pasture", age=57,
        look=Look(skin=3, hair=3, cloth=5, hair_style="bun", hat="straw",
                  version=15, apron=True),
        traits={"curiosity": 0.45, "sociability": 0.60, "diligence": 0.85,
                "grumpiness": 0.35, "creativity": 0.30},
        bio=("Keeps the village flock on the east pasture and can name every "
             "ewe by the sound of its bell. She has strong views on fences, "
             "dogs and people who leave gates open."),
        quirk="counts the flock out loud and always arrives at the same number",
        voice=Voice(rate=140, volume=0.85, hint="zira"),
        schedule=DAY,
    ),
    Persona(
        key="ivo", name="Ivo Thrum", job="beekeeper", home="ivo", work="apiary",
        age=44,
        look=Look(skin=4, hair=0, cloth=3, hair_style="short", hat="hood",
                  version=16, beard=True),
        traits={"curiosity": 0.75, "sociability": 0.35, "diligence": 0.70,
                "grumpiness": 0.25, "creativity": 0.50},
        bio=("Tends the hives behind the east lane. Speaks softly, moves slowly "
             "and has never been stung on a day he expected to be. Sells honey "
             "to the tavern and advice to anyone who stands still."),
        quirk="apologises to the bees before opening a hive",
        voice=Voice(rate=135, volume=0.6, hint="david"),
        schedule=DAY,
    ),
    Persona(
        key="greta", name="Greta Fenn", job="woodcutter", home="greta",
        work="woodlot", age=31,
        look=Look(skin=2, hair=5, cloth=6, hair_style="wild", hat="cap",
                  version=17),
        traits={"curiosity": 0.40, "sociability": 0.55, "diligence": 0.95,
                "grumpiness": 0.45, "creativity": 0.35},
        bio=("Works the south woodlot with a borrowed axe and an unborrowed "
             "opinion about how it should be swung. Fells, splits and stacks "
             "all day, then beats the smith at arm wrestling on Sundays."),
        quirk="judges every tree by how well it will burn",
        voice=Voice(rate=165, volume=0.95, hint="mark"),
        schedule=DAY,
    ),
    Persona(
        key="corin", name="Corin Slate", job="miner", home="corin",
        work="quarry", age=38,
        look=Look(skin=1, hair=4, cloth=7, hair_style="short", hat="cap",
                  version=18, beard=True),
        traits={"curiosity": 0.50, "sociability": 0.30, "diligence": 0.90,
                "grumpiness": 0.65, "creativity": 0.25},
        bio=("Runs the little quarry at the west edge of the village. Comes "
             "back grey with dust, says the stone talks if you listen, and "
             "has never once been convinced to take a day off."),
        quirk="taps every wall twice before trusting it",
        voice=Voice(rate=145, volume=0.9, hint="david"),
        schedule=DAY,
    ),
    # -- v0.3 kids -------------------------------------------------------
    Persona(
        key="nettle", name="Nettle Hollow", job="child", home="pip", work="school",
        age=8, child=True, parent="pip",
        look=Look(skin=0, hair=2, cloth=4, hair_style="wild", hat="straw",
                  version=12),
        traits={"curiosity": 0.98, "sociability": 0.85, "diligence": 0.20,
                "grumpiness": 0.20, "creativity": 0.90},
        bio=("Pip's youngest. Knows every shortcut, every loose board and the "
             "name of every frog in the pond. Has never once arrived anywhere "
             "by the path she was told to take."),
        quirk="collects interesting stones and gives them to serious adults",
        voice=Voice(rate=215, volume=0.8, hint="zira"),
        schedule=KID,
    ),
    Persona(
        key="jory", name="Jory Bell", job="child", home="orin", work="school",
        age=10, child=True, parent="orin",
        look=Look(skin=1, hair=0, cloth=3, hair_style="short", hat="",
                  version=13),
        traits={"curiosity": 0.75, "sociability": 0.90, "diligence": 0.35,
                "grumpiness": 0.35, "creativity": 0.55},
        bio=("Orin's boy. Can smell bread from the far side of the square and "
             "has strong opinions about which loaves are best. Wants to know "
             "why everything is the way it is, especially rules."),
        quirk="negotiates bedtimes as though they were trade agreements",
        voice=Voice(rate=205, volume=0.85, hint="mark"),
        schedule=KID,
    ),
    Persona(
        key="pella", name="Pella Tock", job="child", home="bram", work="school",
        age=12, child=True, parent="bram",
        look=Look(skin=2, hair=5, cloth=1, hair_style="long", hat="cap",
                  version=14),
        traits={"curiosity": 0.70, "sociability": 0.65, "diligence": 0.60,
                "grumpiness": 0.30, "creativity": 0.65},
        bio=("Bram's daughter. Already helps with the measuring and already "
             "knows she will be a builder, though she has not told him yet. "
             "Keeps a tally of how many nails the town hall has eaten."),
        quirk="carries a pencil behind one ear and a plan behind the other",
        voice=Voice(rate=190, volume=0.8, hint="zira"),
        schedule=KID,
    ),
]

BY_KEY = {p.key: p for p in ROSTER}
