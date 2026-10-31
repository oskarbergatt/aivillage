# Stretch ideas and milestone plans

## 18. Stretch

House interiors; recurring visitor cast on top of random; seasonal palette; moon phases;
postcard PNG export; multi-day story arcs; dialogue threads; festival/storm events.

## 19. v0.2 — closing the gaps (implementation plan)

Scope chosen by the user: **everything on the deferred/stretch list**.

1. **Reality** — real holiday/festival calendar (DE-aware, Easter computus), Saturday market,
   Monday repairs, storm-prep warning, forecast-aware work planning, temperature wardrobe,
   moon phase, seasonal palette.
2. **News** — automatic per-feed exponential backoff + mute, live feed-health settings panel,
   Bright Sky/DWD alert courier bulletins (LLM-retold), retry-muted-feeds action.
3. **Social** — persistent per-villager dialogue threads (saved), group conversations (3–4
   villagers), explicit relationship stages (rival → close friend) and stage-change chronicle.
4. **World** — named construction queue at the town-hall site (foundation → walls → roof → bell),
   Saturday market activity, house interiors overlay, visitor trade offers.
5. **UI/UX** — in-game settings modal (language, voice, ambient, news, alerts, save slot, feeds,
   cost), on-screen LLM cost/token meter, save slots (1–5), photo mode (P), postcard export
   (Ctrl+P), README screenshots.
6. **Packaging** — `python -m aivillage`, console entry point, PyInstaller spec.
7. **Tests/docs** — new unit tests for every deterministic subsystem; update PLAN, PROGRESS,
   DECISIONS, README, config.example.toml; bump version to 0.2.0.

Acceptance: `pytest -q` green; headless day/night screenshots render; every item above is
reachable in-game without a config edit where a toggle makes sense; no new blocking network
calls on the render thread.

## 20. v0.3 — jobs, children and self-authored villagers

Scope chosen by the user: **add kids, subscription connectors, more jobs, and let the AIs control
their own character.**

1. **Jobs** — a registry (`agents/jobs.py`) is now the source of truth: 16 adult trades, work tasks,
   tools, sites, yields and the `child` role. Brain task/tool/yield tables are derived from it.
2. **Children** — three kids (Nettle, Jory, Pella) live with existing parents, use a school/play
   timetable, have smaller sprites and shadows, and never yield resources.
3. **Subscription connectors** — `claude_cli`, `codex_cli` and `subscription` providers spawn the
   official logged-in CLIs (`claude -p`, `codex exec`), handle Windows npm `.cmd` shims, parse JSON
   output, prefer the CLI's last-message file for Codex, and report failures loudly.
4. **Self-direction** — the model may return a new trade, ambition, bio, quirk, hat and outfit.
   `Agent.apply_self()` validates every field against the registry and sprite options; children may
   only set a `dream_job`. Runs periodically with a real provider, manually via `R`/SELF, and never
   in mock mode.
5. **World/UI** — four new houses, a school point, a windmill and mill point; inspector shows age,
   dream and ambition; `J` opens the Callings panel; HUD gains SELF and JOBS buttons.
6. **Tests/docs** — `tests/test_jobs_self.py` and `tests/test_llm_cli.py`; fixed-date test fixture;
   README, PLAN, PROGRESS, DECISIONS, config and env examples updated; version 0.3.0.

Acceptance: `pytest -q` green (81 passed); no villager can acquire an unknown job or invalid look
from a model; mock mode remains deterministic; subscription failures surface in the HUD/status.
Known blocker: live subscription verification (Claude account card check) was not possible here.

## 21. v0.4 — four more resource trades

Scope chosen by the user: **new resource jobs, each with a villager and a visible work site.**

1. **Jobs** — `shepherd`, `woodcutter`, `miner` and `beekeeper` join the registry, bringing it to
   20 adult trades. Their tools (`staff`, `axe`, `pick`, `smoker`) are drawn as sprite overlays.
2. **Villagers** — Maude Ash (shepherd), Ivo Thrum (beekeeper), Greta Fenn (woodcutter) and Corin
   Slate (miner) arrive with their own houses, looks, voices, traits, bios and quirks, raising the
   roster to 16 adults + 3 children.
3. **World** — four new houses on the east and south edges, a fenced east pasture with sheep, an
   apiary ringed by hives, a south woodlot with stacked cordwood, and a west quarry of boulders.
   Footpaths connect each site to its worker's door and the existing lanes.
4. **Economy** — the new trades feed the existing stores rather than adding a new resource:
   shepherd and beekeeper produce food, woodcutter produces wood, miner produces stone.
5. **Tests/docs** — world landmark/home coverage, a reachability test for every new job, sprite and
   tool checks; README, PLAN, PROGRESS, DECISIONS and version 0.4.0.

Acceptance: `pytest -q` green (82 passed); each new trade has exactly one adult worker, a home door
and a walkable work site reachable from that door; no new resource storage or save migration needed.
