# aivillage — Master Build Plan

> **Status: IMPLEMENTED (v0.3 — jobs, children and self-authored villagers)** · Last updated: 2026-10-31
> Target: `C:\Users\Oskar\Documents\aivillage`
> This file is the source of truth for the project. The original planning copy lives at
> `C:\Users\Oskar\.opencode\plan\aivillage.md`; this repo copy is now authoritative.
> Deviations from the original plan are logged in [`docs/DECISIONS.md`](docs/DECISIONS.md)
> and tracked in [`PROGRESS.md`](PROGRESS.md).

**Vision:** a desktop pixel-art village that runs on the player's real clock, real weather and real
news, inhabited by fifteen AI villagers — twelve working adults and three children — who work their
jobs, socialise in their free time, receive travelling strangers carrying adapted real-world
headlines, and, with a real model, decide for themselves who they want to become.

---

## 0. Implementation status at a glance

| Area | Status | Where |
|---|---|---|
| Python 3.12 venv, pygame-ce, headless test setup | ✅ done | `pyproject.toml`, `.venv` |
| Live clock, real date/season, sunrise/sunset, fast-forward + return to live | ✅ done | `aivillage/reality/clock.py` |
| Auto location (ipwho.is) + city override, disk cache | ✅ done | `aivillage/reality/geo.py` |
| Open-Meteo weather, 15-min refresh, cache, seasonal fallback | ✅ done | `aivillage/reality/weather.py` |
| 64×48 procedural map, houses, farm, pond, school, windmill, workshop, tavern, town-hall site | ✅ done | `aivillage/world/` |
| Procedural pixel art (tiles, villagers, houses, props, night variants) | ✅ done | `aivillage/assets/sprites.py` |
| Fifteen villagers (12 adults + 3 children), traits, needs, schedules, A* movement | ✅ done | `aivillage/agents/` |
| Job registry: 16 adult trades + child role, task/tool/yield definitions | ✅ done | `aivillage/agents/jobs.py` |
| Kids: school/play timetable, smaller sprites, parents, dream jobs, no resource yield | ✅ done | `aivillage/agents/roster.py`, `brain.py` |
| Jobs, farm cycle, resources, town-hall construction, chronicle | ✅ done | `aivillage/agents/brain.py`, `aivillage/app.py` |
| Sunday rest, weather-aware work breaks, night folk schedules | ✅ done | `aivillage/agents/brain.py`, `roster.py` |
| Real holiday/festival calendar, Saturday market/Monday routines, forecast-aware planning | ✅ done | `aivillage/reality/calendar.py`, `brain.py` |
| LLM-only chat, provider-agnostic adapters, worker queue, cache, mock | ✅ done | `aivillage/llm/` |
| Subscription connectors: Claude Code (`claude -p`), Codex (`codex exec`), auto-pick | ✅ done | `aivillage/llm/client.py` |
| Villager self-direction: validate and apply job/ambition/bio/quirk/hat/outfit | ✅ done | `app.py`, `brain.py`, `prompts.py` |
| Ambient conversations (free-time gated), affinity/memory effects | ✅ done | `aivillage/app.py`, `prompts.py` |
| Travellers: procedural strangers, bell assembly, dispatch, reactions | ✅ done | `aivillage/agents/visitor.py`, `news/pipeline.py` |
| 29 keyless RSS feeds, dedupe, distress filter, weighted selection | ✅ done | `aivillage/news/` |
| EN/DE runtime switch, locale parity, per-language prompts/feeds | ✅ done | `aivillage/locales/`, `i18n.py` |
| Offline SAPI5 voice (pyttsx3), per-villager voice profiles, mute | ✅ done | `aivillage/voice/tts.py` |
| Procedural SFX + weather VFX (rain/snow/fog/storm, wind) | ✅ done | `assets/sfx.py`, `render/renderer.py` |
| Save/load + autosave | ✅ done | `aivillage/save.py`, `app.py` |
| Tests (81 passing) | ✅ done | `tests/` |
| News status/health panel, automatic feed backoff/mute | ✅ done | `news/pipeline.py`, HUD |
| DWD/Bright Sky alert service | ◐ partial | module exists; courier bulletins not wired |
| In-game settings screen | ✗ deferred | settings via config/CLI |
| Save slots 1–5 | ◐ partial | `save.py` ready; HUD still uses slot 1 |
| Multi-turn ambient exchanges (single exchange per pairing) | ◐ partial | `prompts.exchange_*` |
| Group chats at plaza lunch | ◐ partial | prompt helper only; assembly + pair chats |
| Persistent conversation threads across days | ◐ partial | memory helpers exist; not used by scheduler |
| Cost meter in HUD | ◐ partial | `LLMClient.cost_text()` exists, not drawn |
| Setup card with "test connection" | ◐ partial | setup card explains missing model; retry button |
| Weather forecast-aware planning, wardrobe | ◐ partial | forecast-aware work; no wardrobe |
| Screenshots in README | ✗ not captured | F12 saves to `data/` |

Legend: ✅ implemented · ◐ partial/limited · ✗ not implemented.

---

## 1. Locked decisions

| Area | Decision |
|---|---|
| Stack | Python 3.12 (uv venv), pygame-ce, numpy, requests, feedparser, python-dotenv, pyttsx3, SQLite, pytest |
| Interpreter | Do NOT use system Python 3.14.3. `uv venv --python 3.12` |
| Rendering | **Native-resolution window + integer camera zoom** (see Decisions #1) |
| Art | 100% procedural pixel art; bundled OFL pixel fonts |
| Time | Live mode — village clock == real clock; real date/season/sunrise/sunset |
| Weather | Open-Meteo (keyless), auto-detected location, 15 min refresh, disk cache |
| Location | ipwho.is auto-detect (Rostock 54.0887/12.1405, Europe/Berlin), overridable |
| Dialogue | LLM-only, provider-agnostic (Ollama/OpenAI/Anthropic/OpenAI-compatible) |
| Subscriptions | Official logged-in CLIs (`claude -p`, `codex exec`), never scraped web sessions |
| Voice | pyttsx3 / SAPI5 offline only, per-villager profiles |
| News tone | Neutral, filtered for distress |
| Visitors | Always newly generated random travellers |
| Language | Switchable at runtime: en / de |
| Interaction | Observer: pan/zoom, inspect, chat, speed, chronicle, save/load |

## 2. Verified environment / APIs

- Python 3.14.3 default, pygame absent; uv has CPython 3.12.12.
- Open-Meteo current+daily: 8.9 °C, WMO 3, sunrise 06:58, sunset 16:40 (plan-time probe).
- ipwho.is: Rostock, Germany, 54.0886733 / 12.1404851, Europe/Berlin.
- geocoding-api.open-meteo.com works; Bright Sky DWD alerts reachable (0 active).
- Runtime checks: the app degrades to cached/seasonal weather when offline.

### Verified news feeds (29, feedparser-tested)

World EN: BBC World 36, Guardian World 45, Guardian UK 140, NPR 10, Al Jazeera 25,
DW English 10, France24 24, Euronews 50, CBC World 20, ABC AU 25, UN News 30, Sky News 8.

World DE: Tagesschau 40, ZDF heute 166 (https://www.zdf.de/rss/zdf/nachrichten),
Deutschlandfunk 40, Spiegel 30, Zeit Online 15, taz 50.

Tech: Hacker News 20, Ars Technica 20, Heise 159, The Verge 10.
Science: NASA 10, Nature 75, Phys.org 30, ScienceDaily 60.
Oddities: Atlas Obscura 27. Sport: BBC Sport 69, ESPN 48.

Rejected: AP News 403, Ostsee-Zeitung 403, NDR MV no RSS, SVZ no RSS, Wikipedia Current Events not RSS.
=> local category falls back to national German feeds.

## 3. Reality layer

Clock: live default; speed buttons detach into Fast-Forward with badge + "Return to Live";
re-sync on sleep/resume; real sunrise/sunset drives lighting; Sunday rest for day folk; real
holidays and Saturday/Monday routines are **not** implemented yet; night = sleeping village +
night folk (Wisp, Nim) + "Sleep until dawn" (N).

Weather: poll 15 min, cache, fallback last_known/seasonal_sim. WMO map:
0 clear | 1–2 partly cloudy | 3 overcast | 45/48 fog | 51–57 drizzle | 61–67 rain |
71–77 + 85–86 snow | 80–82 showers | 95–99 thunderstorm.
Effects: rain, snow, fog, lightning, wind-driven particles, night lighting and warm window pools.
Forecast-aware planning; temperature wardrobe (<8 °C coats, >25 °C shade); weather text in prompts;
DWD alerts as courier bulletins — **not implemented yet**.

## 4. World

64×48 map, 16 px tiles, seeded. Grass, dirt paths, pond, trees, rocks, flowers, fences, lamps, road.
8 houses, farm plots, workshop, well, plaza, market stall, tavern, town-hall build site.
Autotiling; A* walkable grid; agent soft avoidance.

## 5. Villagers

| Villager | Job | Hook |
|---|---|---|
| Marrow Vane | Blacksmith | gruff, blunt, tender about his anvil |
| Pip Hollow | Farmer | cheerful, distractible, turnip-obsessed |
| Sable Quill | Artist | dreamy, dramatic, metaphors |
| Orin Bell | Baker | warm, gossipy, feeds everyone |
| Hazel Reed | Herbalist | calm, cryptic, answers with questions |
| Bram Tock | Builder | methodical, proud joints, grumpy about bad measures |
| Nim Farrow | Fisher | patient, superstitious, long silences |
| Wisp | Forager | eerie, poetic, nocturnal |
| June Alder | Teacher | patient, exact, secretly writes terrible poems |
| Fen Marle | Miller | flour-dusted, practical, hates a still wind |
| Mira Sloe | Weaver | observant, dry, dyes with whatever grows |
| Tobin Rusk | Tinker | restless, cheerful, mends everything but his cart |
| Nettle Tock | Child (Bram's) | blunt, brave, asks the questions adults avoid |
| Jory Bell | Child (Orin's) | dreamy, hungry, trades stories for crusts |
| Pella Tock | Child (Bram's) | methodical, ambitious, keeps a nail tally |

Children have a `child` role rather than an adult trade. They attend lessons, play, and may choose a
`dream_job` through self-direction; they never produce resources. Adults may change trade through
self-direction, validated against `agents/jobs.py`.

Traits: curiosity, sociability, diligence, grumpiness, creativity.
Needs: hunger, energy, social, fun. Plus mood, schedule, home, work site, memory log, affinity matrix.

Priority ladder (implemented as schedule block → survival overrides → intent):
0 survival (interrupts all)
1 job shift (interrupts 2+)
2 communal duty (market, news assembly, storm prep, festival)
3 breaks (lunch, dinner, tea)
4 free time (socialise, hobbies, wander, visit friend)
5 idle

Conversations only in tiers 3–4. `work_chatter` false by default.
Job queues quantified + visible ("3 plots watered", "2 beams fitted", "1 batch of loaves");
Town Hall progress is visible and named in the chronicle; job satisfaction feeds mood.

Daily blocks: wake → wash → breakfast → commute → work → lunch social → work → hobby →
dinner → wind-down → sleep.

## 6. Simulation

20 Hz logic / 60 fps render (logic clamped per frame, render independent).
Utility-ish scoring from needs × personality × time × weather.
Economy: wood/stone/food/coin. Farm seed→sprout→ripe→harvest. Affinity drift, grudges, gossip.
Events: weather, visitors, construction milestones. Additive light overlay. Weather VFX + particles.

## 7. Conversations

Pair available villagers (tier 3/4) near each other. One LLM call → one exchange
(multi-turn arrays supported by the prompt/response shape).
Sequential bubbles with speaker colour/portrait; face each other.
Persistent threads across days: memories persist, thread objects do not.
Gossip propagates memories. Affinity/mood/memory consequences.
Throttle `social.ambient_budget_s` (default 20 s); player chat never throttled.

## 8. News pipeline

Poll ~40 min via feedparser (UA, timeout) → dedupe hash → SQLite `news.db` (21-day prune) →
distress filter → weighted category pick (world 40, oddities 15, science 15, tech 10, sport 10,
local 10; never same source twice in a row; language matched) → LLM adapts ONCE per item+language
→ dispatch {headline, tone, topic}. Originals kept in Chronicle with source URL.
Feed health counters are exposed via `NewsService.status()`; automatic mute-after-5-failures is
not implemented. Offline: rumours/omens instead.

## 9. Travellers

Always newly generated: procedural name, palette, trade, origin, personality, voice.
Spawn at map edge → plaza → bell → tier-2 assembly → deliver dispatch (bubble + TTS) →
reactions → market/tavern → leave (~45 min). 1–3 arrivals/day + random social visits.
Attendees remember dispatch; news spreads by gossip; bad news sours moods, good news celebrates.

## 10. Language

`language = en|de`, switchable at runtime (F2 / HUD button). `locales/en.json`, `de.json`.
LLM prompted in active language; dispatch cache per language; feed pool swaps
(DE: Tagesschau/ZDF/DLF/Spiegel/Zeit/taz/Heise); TTS picks matching SAPI voice;
umlaut glyph check; locale formatting.

## 11. LLM

`[llm] provider = ollama|openai|anthropic|openai_compatible|claude_cli|codex_cli|subscription|mock|none`,
model, base_url, api_key_env, temperature, max_tokens, ambient_dialogue.
Adapters per provider; subscription adapters spawn the signed-in official CLI with a short prompt and
parse its JSON/plain output. Worker thread + queue; "…" bubbles.
Prompt = persona + time/weather/needs/location/memories/relations/news threads/language →
strict JSON {line, emotion, action, topic}. Fallback to plain text if JSON fails. History capped,
response cache, rate limited. Setup card explains a missing model with a retry button.
Daily chronicle/diary at dawn.
Self-direction adds a `self` job: the model returns ambition, bio, quirk, a job (or `dream_job` for a
child), hat and outfit; `Agent.apply_self()` validates and persists it.

## 12. Voice

pyttsx3 on its own thread + speak queue. Per-agent SAPI voice + rate + volume. Speaks player chat
and notable events; ambient silent by default; global mute always works. No pitch control in SAPI5.

## 13. UI

HUD: date/season, clock, weather + temp, resources, speed, mute, save, language, traveller, jobs.
Inspector: portrait, job/age/dream, ambition, traits, needs, mood, relationships, current task,
thought, separate TALK and SELF buttons.
Callings panel (`J`): all trades, who holds each, yields.
Chronicle: dispatches with real source links, daily diary, events.
Settings: language and save work in HUD; location/provider are config/CLI options (**no modal
settings screen**).
Keys: Space pause, 1–4 speed, L return to live, N sleep until dawn, M mute, S save, T chat, R self,
J jobs, C chronicle, V visitor, F2 language, F12 screenshot, WASD/drag pan, wheel zoom, Esc close.

## 14. Layout

`run.py`, `pyproject.toml`, `config.example.toml`, `.env.example`, `PLAN.md`,
`PROGRESS.md`, `README.md`, `docs/DECISIONS.md`

```
aivillage/
  app.py config.py i18n.py save.py
  locales/{en,de}.json
  assets/{palette,sprites,font,sfx}.py  assets/fonts/*.ttf
  world/{mapgen,objects,pathfinding}.py
  agents/{persona,roster,brain,needs,memory,animator,visitor}.py
  llm/{client,prompts}.py
  news/{pipeline,filters,store,sources}.py
  voice/tts.py
  reality/{clock,weather,geo}.py
  render/{camera,renderer,ui}.py
tests/
```

## 15. Milestones

M1 Skeleton + reality: uv venv 3.12, window, fixed-step loop, camera, mapgen, tiles, fonts (umlaut
check), HUD shell, real clock + weather + location + cache, day/night lighting, save skeleton.

M2 Villagers at work: 8 villager sprites, walk cycles, A*, priority ladder, utility AI, needs,
real-time schedules, job queues + props + stockpile, farm cycle, town-hall site, forecast planning,
weekday/holiday routines, temperature wardrobe.

M3 Free-time minds: inspector, LLM adapters + worker + setup screen, player chat, gated conversation
scheduler, multi-turn exchanges, threads, gossip, daily chronicle, i18n + runtime switch.

M4 Travellers + news: 29 feeds + DWD alerts, SQLite dedupe, health, distress filter, weighted
selection, language matching, LLM adaptation + cache, procedural travellers, bell assembly,
delivery + reactions, market/tavern, news propagation, settings screen.

M5 Voice + polish: pyttsx3 thread + profiles + mute + per-language voices, procedural SFX/ambience,
weather VFX, holidays, particles, tests, README with screenshots.

## 16. Verification per milestone

Launch for real; day + night screenshots reviewed; click villager and verify inspector/task;
real chat round-trip; confirm UI never blocks on network; pytest green.

**Current verification:** pytest 81 passed; headless launches with `--provider mock` produce a
rendered frame; day/night renders verified by luminance assertion in `tests/test_app.py`. The
subscription CLIs are installed and unit-tested, but `claude -p` returned an account card-verification
error in the build environment and Codex was not exercised with a real prompt. A real desktop launch
and visual review are still outstanding.

## 17. Risks & known gaps

- 3.14 wheel gaps → uv 3.12. pyttsx3 flaky enumeration → try/except + mute + override.
- LLM-only means no dialogue without config → setup card. Cost/latency → cache + throttle (no
  on-screen cost meter yet).
- Night launches → sleeping village + sleep button. Long sessions → clamp catch-up.
- Font umlauts → verify/fallback. Feed rot → health counters (auto-mute missing).
- Not implemented yet: courier wiring for DWD alerts, in-game settings modal, cost meter, save-slot
  picker in the HUD, group lunch chats in the live scheduler, persistent threads in the live
  scheduler, wardrobe, README screenshots.

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
