"""The village job registry.

A job says where a villager works, what they are seen doing, which tool they
hold, and what the village gains when a task completes.  Keeping this in one
place means new jobs can be added without touching the simulation, and the
self-direction prompt can offer the same list the game actually understands.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    key: str
    work: str                       # world point name
    tasks: tuple[str, ...]
    tool: str = ""
    resource: str = ""              # food | wood | stone | coin | progress | ""
    amount: float = 0.0
    indoor: bool = False            # shelter from bad weather
    school: bool = False           # children are here during lessons
    child: bool = False             # only children may hold this job


JOBS: dict[str, Job] = {
    "blacksmith": Job(
        "blacksmith", "workshop",
        ("heating iron", "hammering a blade", "quenching steel", "mending a plough"),
        "hammer", "coin", 2.0, indoor=True),
    "farmer": Job(
        "farmer", "farm",
        ("watering the plots", "pulling weeds", "harvesting turnips", "sowing seeds"),
        "hoe", "food", 3.0),
    "artist": Job(
        "artist", "home_sable",
        ("sketching the plaza", "mixing pigment", "painting the light", "scraping a mistake"),
        "brush", "coin", 1.0, indoor=True),
    "baker": Job(
        "baker", "home_orin",
        ("kneading dough", "watching the oven", "carrying loaves to market"),
        "basket", "food", 2.0, indoor=True),
    "herbalist": Job(
        "herbalist", "woods_west",
        ("gathering herbs", "sorting roots", "brewing a tincture", "hanging bundles to dry"),
        "basket", "food", 1.0),
    "builder": Job(
        "builder", "buildsite",
        ("fitting a beam", "sawing planks", "hammering nails", "checking the level"),
        "hammer", "progress", 0.05),
    "fisher": Job(
        "fisher", "pond",
        ("casting the line", "waiting for a bite", "reeling in", "mending the net"),
        "rod", "food", 1.0),
    "forager": Job(
        "forager", "woods_east",
        ("searching the treeline", "collecting mushrooms", "checking snares"),
        "basket", "wood", 2.0),
    # -- v0.3 professions ------------------------------------------------
    "teacher": Job(
        "teacher", "school",
        ("hearing the children's letters", "writing on the slate",
         "settling an argument about sums", "reading aloud"),
        "", "coin", 1.0),
    "miller": Job(
        "miller", "mill",
        ("hauling sacks", "setting the mill wheel", "brushing flour off",
         "weighing a sack"),
        "basket", "food", 3.0, indoor=True),
    "weaver": Job(
        "weaver", "home_mira",
        ("working the loom", "dyeing thread", "mending a cloak", "carding wool"),
        "", "coin", 2.0, indoor=True),
    "tinker": Job(
        "tinker", "workshop",
        ("mending a pot", "sorting nails", "sharpening a hinge", "fixing a kettle"),
        "hammer", "coin", 2.0, indoor=True),
    "innkeeper": Job(
        "innkeeper", "tavern_door",
        ("wiping the boards", "ladling stew", "airing the beds", "counting the night's coin"),
        "basket", "food", 2.0, indoor=True),
    "scribe": Job(
        "scribe", "plaza",
        ("copying the council's letters", "trimming a quill",
         "reading the notices aloud", "keeping the village roll"),
        "brush", "coin", 1.0),
    "guard": Job(
        "guard", "road",
        ("walking the road", "checking the gate", "watching the treeline",
         "greeting a traveller"),
        "", "coin", 1.0),
    "musician": Job(
        "musician", "plaza",
        ("tuning a pipe", "playing for the square", "teaching a child a tune"),
        "", "coin", 1.0),
    "child": Job(
        "child", "school",
        ("playing tag", "skipping stones", "chasing the geese",
         "drawing with chalk", "asking impossible questions"),
        "", "", 0.0, child=True),
}

JOB_KEYS = tuple(JOBS)
ADULT_JOBS = tuple(k for k, j in JOBS.items() if not j.child)


def job_for(key: str) -> Job:
    return JOBS.get(key, JOBS["child"] if key == "child" else JOBS["farmer"])


def job_label_key(key: str) -> str:
    return f"job.{key if key in JOBS else 'farmer'}"


def job_choices(child: bool = False) -> list[dict]:
    """A compact list used in prompts and the jobs panel."""
    keys = ("child",) if child else ADULT_JOBS
    return [{"key": k, "work": JOBS[k].work,
             "tasks": list(JOBS[k].tasks[:2])} for k in keys]
