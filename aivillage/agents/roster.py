"""The eight villagers."""
from __future__ import annotations

from .persona import Look, Persona, Voice

DAY = [(6.5, 7.5, "meal"), (7.5, 12.0, "work"), (12.0, 13.0, "meal"),
       (13.0, 17.0, "work"), (17.0, 18.5, "free"), (18.5, 19.5, "meal"),
       (19.5, 22.0, "free"), (22.0, 30.0, "sleep")]

NIGHT = [(0.0, 1.0, "free"), (1.0, 8.0, "sleep"), (8.0, 16.0, "sleep"),
         (16.0, 19.0, "free"), (19.0, 23.0, "work"), (23.0, 24.0, "free")]


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
]

BY_KEY = {p.key: p for p in ROSTER}
