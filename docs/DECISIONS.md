# Decisions log

Deviations from [`PLAN.md`](../PLAN.md), and the reasons behind them. Newest entries at the bottom.
Each entry records *what changed*, *why*, and *what it costs*.

---

## 1. Native-resolution window instead of a 480×270 buffer

**Planned:** render the world into a 480×270 surface, then integer-scale/letterbox it.
**Actual:** create a native window (default 1440×810, minimum 960×600, resizable) and scale the
*world* by an integer camera zoom (2–5, default 3). HUD/UI is drawn at native resolution.

**Why:** at 480×270 the Silkscreen UI is unreadable, and the inspector/chat panels need far more
space than the tiny buffer allows. Native UI also keeps text crisp on high-DPI screens.

**Cost:** world pixels are chunky only at the camera zoom level, not globally; the UI is not
"pixel-scaled" as a whole. `Camera` clamps the window to at least 960×600.

## 2. Frame-scaled simulation instead of a fixed 20 Hz accumulator

**Planned:** 20 Hz logic / 60 fps render.
**Actual:** one update per frame with a clamped `dt`, multiplied by the time speed (0 when paused,
1 in live mode). Render and logic share the frame.

**Why:** the simulation is cheap (8 agents + few visitors), and a fixed-step accumulator would add
complexity for no visible benefit. Clamping prevents catch-up explosions after sleep/resume.

**Cost:** behaviour is frame-rate dependent in principle; on very low frame rates agents move in
larger steps. The movement code consumes a distance budget, so paths still complete correctly.

## 3. Schedule + survival overrides instead of a full utility scorer

**Planned:** utility scoring across needs, personality, time, weather and forecast.
**Actual:** a schedule block (`sleep/meal/work/break/free`) is chosen from the persona timetable;
survival overrides (low energy → nap, low hunger → eat) interrupt it; weather can turn outdoor
work into shelter. Free time picks a wander target with weighted randomness.

**Why:** predictable routines are the point of the village; a full scorer made villagers cancel
jobs constantly and produced less readable behaviour.

**Cost:** less emergent variety; the "priority ladder" exists conceptually (survival > job >
communal > break > free > idle) but is not a numeric score. Forecasts are not consumed yet.

## 4. One exchange per ambient pairing; no persistent threads or group chats

**Planned:** multi-turn exchanges, persistent threads across days, group chats at plaza lunch.
**Actual:** an ambient conversation is one LLM call that may contain several turns; the result is
played as sequential bubbles. Up to three ambient conversations can overlap; pairings are throttled
by `social.ambient_budget_s` (20 seconds by default). Memories and
affinity persist; conversation objects do not. The plaza "assembly" is used for traveller
announcements, not lunch group chat.

**Why:** multi-turn threads and group orchestration multiply LLM cost and latency, and the
single-exchange format already reads well in bubbles.

**Cost:** no running jokes or callbacks to yesterday's conversation beyond stored memories.

## 5. `mock` provider added

**Planned:** Ollama / OpenAI / Anthropic / OpenAI-compatible only.
**Actual:** a `mock` provider that returns deterministic JSON for chat, exchange, dispatch and
rumour jobs.

**Why:** the village must be runnable and testable with no model, no key and no network. It also
makes CI deterministic.

**Cost:** mock dialogue is intentionally flat and must never be presented as real quality.

## 6. News retention 21 days, no automatic feed mute, no DWD alerts

**Planned:** 30-day store, backoff/mute after 5 failures, Bright Sky DWD alerts as bulletins.
**Actual:** items are pruned after 21 days; per-source errors are counted and exposed via
`NewsService.status()`; no automatic mute. Bright Sky was probed during planning but is not wired
into the pipeline.

**Why:** 21 days is enough for "never repeat a story too soon" in a village that gets 1–2
dispatches/day, and the health UI is more useful than silently disabling a source. DWD alerts
need a second API and a language-mapping layer; deferred rather than half-done.

**Cost:** a permanently broken feed keeps being retried every poll. Severe-weather bulletins are
missing.

## 7. No modal settings screen

**Planned:** settings screen for language, location, provider, sources, voice, speed.
**Actual:** language (F2/button), mute, speed, save, traveller are in the HUD. Location, provider,
model, zoom and window size are `run.py` flags or `config.toml`. The setup card explains a missing
model and offers a retry.

**Why:** a modal settings UI would duplicate config/CLI behaviour and needs validation, focus
handling and persistence. The observer interaction model is better served by a small HUD.

**Cost:** changing location/provider requires a restart; discovering options requires the README.

## 8. Weather effects limited to what reads at village scale

**Planned:** cloud shadows, fog, rain + puddles, snow + footprints, lightning, wind sway, smoke.
**Actual:** rain, drizzle, snow, fog, storm flashes and wind-driven particles; night lighting with
warm window pools and lamp glow.

**Why:** puddles/footprints/smoke need per-tile state and extra sprites, and at 16 px tiles they
turned into noise. The retained effects communicate weather clearly.

**Cost:** less environmental storytelling; no accumulation or footprints.

## 9. SAPI5 per-villager voices use voice/rate/volume only

**Planned:** per-villager distinct voices.
**Actual:** each persona maps to a preferred SAPI voice (language-matched), plus rate and volume
scaling. If enumeration fails, a fallback voice is used and the UI still works.

**Why:** SAPI5 exposes no pitch control, and many Windows installs only ship one or two voices.

**Cost:** voices may sound more similar than intended on minimal Windows installs; German text uses
the German voice when present, otherwise the default voice.

## 10. Location resolution is automatic, with a Rostock default

**Planned:** auto-detect via ipwho.is, overridable.
**Actual:** `LocationService` tries cached location → ipwho.is → Rostock fallback; `--location`
uses Open-Meteo geocoding. There is no in-game location picker.

**Why:** zero-setup is a hard requirement, and the project was developed in Rostock; the fallback
keeps weather/season plausible when offline or when IP geolocation is blocked.

**Cost:** a user elsewhere gets Rostock weather until detection succeeds or they pass `--location`.

## 11. Distress filter is deliberately blunt and word-boundary based

**Planned:** neutral tone, filtered for distress.
**Actual:** EN/DE distress word sets matched with `(?<!\w)word(?!\w)` so "deadline" and "total" do
not trip the filter; items are dropped before storage.

**Why:** naive substring matching hid ordinary stories; regex word boundaries fixed that. The word
sets still favour catching violence over completeness.

**Cost:** some sensitive stories slip through under euphemisms; some legitimate stories are dropped.
The filter is intentionally conservative and easy to extend.

## 12. World fixes forced by walkability

- The well moved from `(30,21)` to `(28,20)` so the plaza tile `(31,22)` stays walkable.
- `market_front` moved to `(35,28)` to sit in front of the stall, not inside it.
- The fisher's pond work point moved to the shore at `(45,31)`; the old point was water.
- `Agent.go_to_tile` no longer forces the final point onto a blocked goal; it honours A*'s
  nearest-walkable retarget. Clicking a wall now stops at the wall instead of entering it.

**Why:** three tests and real play both exposed agents standing in water/inside props.

## 13. Two persistence formats

**Actual:** village state (agents, needs, plots, build progress, chronicle, diaries, day number)
is JSON in `saves/`; news items, adapted dispatches and visit history are SQLite in `data/news.db`.

**Why:** the village save is small, human-readable and version-tolerant; news needs dedupe,
per-language caches and pruning, which SQLite does well.

**Cost:** backing up a village means copying both `saves/` and `data/` (the latter is optional —
news refetches).

## 14. Test isolation: injected news DB, mock LLM, no network

**Actual:** `NewsService(config, llm, i18n, db_path=...)` accepts an isolated database. The `app`
fixture uses the mock provider, disables news, forces clear midday weather and a fixed sim clock.
`tests/test_pipeline.py` sets `last_fetch` so a test can never trigger a real feed fetch.

**Why:** the first pipeline run polluted a temporary DB with 300+ live headlines and made
assertions depend on the internet. Tests must be hermetic and fast.

**Cost:** tests exercise the pipeline's logic, not live feed parsing. Feed health is verified
manually during planning.

## 15. Fonts are bundled, not downloaded at runtime

**Actual:** `Silkscreen-Regular/Bold` and `PressStart2P-Regular` live in
`aivillage/assets/fonts/` with their OFL licence files.

**Why:** the game must start offline and the OFL requires the licence to travel with the font.
The earlier idea of fetching fonts on first run added a failure mode for zero benefit.

## 16. Pygame re-initialisation in tests

**Actual:** `VillageApp.shutdown()` calls `pygame.quit()`. The test suite re-initialises pygame
before each test and calls `font.clear_cache()` so cached `Font` objects do not outlive the font
module.

**Why:** otherwise later tests fail with `Invalid font (font module quit since font created)`.

## 17. Separate git repository in the project folder

**Actual:** the project is initialised as its own repository instead of committing a home directory.

**Why:** committing the whole home directory is unsafe and meaningless. A project-scoped repo keeps
diffs reviewable and ignores `.venv/`, `data/`, `saves/`, `config.toml` and `.env`.

**Cost:** when nested in another repository, this project is seen as a separate repository.

## 18. Subscriptions are driven through the official CLIs, not as API keys

**Planned:** "an OpenAI / Anthropic subscription connector".
**Actual:** consumer ChatGPT Plus/Pro and Claude Pro/Max subscriptions are not callable as ordinary
API keys, and scraping a browser session would be fragile and against the services' terms. The
`subscription` connectors instead spawn the official, already-logged-in CLIs (`claude -p` and
`codex exec`), pass the system prompt and user prompt, and parse their output.

**Why:** this is the only supported way to reuse a consumer subscription. It also avoids storing
OAuth tokens or asking for passwords.

**Cost:** each villager line is a separate process and can take seconds; normal subscription rate
limits apply. A failed login or billing check surfaces as an error bubble/toast rather than silent
dialogue. On Windows, npm's `.cmd` shims are wrapped in `COMSPEC /c`; the prompt goes over stdin
because Claude's CLI rejects an empty `--tools` flag followed by an argument.

## 19. Children are a job role, not adult villagers with a smaller sprite

**Actual:** a `child` entry in the job registry owns the school/play schedule. Kids have a `parent`
key, `age`, smaller render scale, no yield, and a `dream_job` field that self-direction can change.
They cannot take an adult trade or produce resources.

**Why:** treating children as ordinary workers made them compete for adult jobs and broke the
economy tests. A separate role keeps the timetable explicit and lets the inspector show "dreams of
builder" without pretending the child is employed.

**Cost:** children are less economically useful by design; the village needs enough adults to keep
wood/stone/food/coin moving.

## 20. Self-authored identity is validated before it touches a villager

**Actual:** the `self` LLM job may return `job`, `dream_job`, `ambition`, `bio`, `quirk`, `hat` and
`outfit`. `Agent.apply_self()` checks the job registry, hat allow-list, outfit range and text
lengths; unknown values are ignored. The same validation runs when restoring a save. Autonomous
self-direction is disabled for the `mock` provider and can be turned off with `llm.self_directed`.

**Why:** a model can hallucinate a trade ("wizard"), an invalid sprite index or a 2,000-character
biography. Validation keeps the world consistent and the mock provider deterministic for tests.

**Cost:** the model cannot invent genuinely new trades or clothing; it chooses from the registry and
the procedural sprite options. Player-triggered self-direction still needs a live provider.

## 21. Tests pin an ordinary Thursday

**Actual:** the shared `app` fixture sets the sim clock to `2026-10-29 10:00` and uses matching
sunrise/sunset. Before this, running the suite on a real holiday (Reformation Day) made every
villager rest and broke production/construction tests.

**Why:** CI must not depend on the calendar of the machine running it.

**Cost:** tests do not exercise the real-date holiday path directly; `reality/calendar.py` covers it
with pure functions and a separate fixed date if needed.

## 22. Resource trades reuse the existing economy and work points

**Actual:** `shepherd`, `woodcutter`, `miner` and `beekeeper` are ordinary `Job` entries. Their yields
are food, wood, stone and food, the same stores the older trades already fill. Each has a named world
point (`pasture`, `woodlot`, `quarry`, `apiary`), a tool overlay and one villager with a matching
`home_<key>` door. The map adds fences, sheep, hives, cordwood and boulders around those points.

**Why:** adding a wool, honey or slate resource would touch the HUD, saves, needs and every balance
test for little visible gain. Reusing the four existing stores keeps the economy readable and the
v0.4 change additive: no new storage, no save migration, and the same `Agent` yield path.

**Cost:** a shepherd and a beekeeper look like they produce food rather than wool and honey. If a
future version wants distinct goods, the job registry is the only place that needs a new resource
name, followed by `app.stats` and the HUD.
