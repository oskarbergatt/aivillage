"""Public facade and controller composition."""
from __future__ import annotations

from .app_shared import (
    ADULT_JOBS,
    Agent,
    AlertCourierMixin,
    AlertService,
    Camera,
    ChatMixin,
    ChatState,
    H,
    I18N,
    JOBS,
    LocationService,
    NewsService,
    P,
    PhotoExportMixin,
    ROSTER,
    Renderer,
    Sfx,
    SimClock,
    TILE,
    UI,
    Visitor,
    VoiceService,
    W,
    WeatherService,
    World,
    datetime,
    job_choices,
    load_slot,
    make_llm,
    math,
    os,
    prompts,
    pygame,
    random,
    save_village,
    slot_path,
    sprites,
    threading,
    time,
    traceback,
)

from .app_services import VillageServicesMixin
from .app_visitors import VisitorsMixin
from .app_social import VillageSocialMixin
from .app_persistence import VillagePersistenceMixin
from .app_controls import VillageControlsMixin
from .app_loop import VillageLoopMixin
from .ambient_setup import AmbientModelSetupMixin
from .social_tracks import SocialTracksMixin
from .gateway_setup import GatewaySetupMixin
from .story_arcs import StoryArcsMixin


class VillageApp(ChatMixin, AlertCourierMixin, PhotoExportMixin, VillageServicesMixin, VisitorsMixin, VillageSocialMixin, VillagePersistenceMixin, VillageControlsMixin, VillageLoopMixin, AmbientModelSetupMixin, SocialTracksMixin, GatewaySetupMixin, StoryArcsMixin):
    def __init__(self, config, new_game: bool = False, seed: int | None = None):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        pygame.font.init()

        self.config = config
        self.i18n = I18N
        self.i18n.set_language(config.language)
        self.seed = int(seed if seed is not None else config.seed)
        self.new_game = new_game

        info = pygame.display.Info()
        width = int(config.get("general.window_width", 1440))
        height = int(config.get("general.window_height", 810))
        width = max(960, min(width, max(960, info.current_w - 80)))
        height = max(600, min(height, max(600, info.current_h - 100)))
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("aivillage")
        self._set_icon()

        self.pyclock = pygame.time.Clock()
        self.running = True
        self.sfx = Sfx(True, 0.8)
        self.voice = VoiceService(config, self.i18n,
                                  {p.key: p.voice for p in ROSTER})
        self.llm = make_llm(config)
        self.uiclock = pygame.time.Clock()

        self.world = World(self.seed)
        self.locations = LocationService(config)
        self.weather_service = WeatherService(config, self.locations)
        self.weather = self.weather_service.current()
        self.clock = SimClock(config, self.weather_service)

        self.rng = random.Random(self.seed * 977 + 13)
        self.agents: list[Agent] = []
        for i, persona in enumerate(ROSTER):
            self.agents.append(Agent(persona, self.world,
                                     random.Random(self.seed + i * 131)))
        self.agent_by_key = {a.key: a for a in self.agents}

        self.camera = Camera(W * TILE, H * TILE,
                             int(config.get("general.zoom", 3)),
                             (width, height))
        self.camera.center_on(*self.world.points.get("plaza", (500, 360)))
        self.renderer = Renderer(self.world, self.camera, self.i18n)
        self.ui = UI(self.i18n)

        self.selected = None
        self.follow_selected = False
        self.chat = ChatState()
        self.show_chronicle = False
        self.show_jobs = False
        self.show_settings = False
        self.show_provider_setup = False
        self.show_ambient_model = False
        self.show_gateway = False
        self.gateway_values = ["", "", ""]
        self.gateway_focus = 0
        self.gateway_error = ""
        self.ambient_model_input = ""
        self.ambient_model_error = ""
        self.setup_provider = str(config.get("llm.provider", "auto"))
        from .setup_download import ModelDownload
        self.setup_download = ModelDownload()
        self.photo_mode = False
        self.save_slot = 1
        self.selected_slot = 1
        self.setup_dismissed = False
        self.self_pending: str | None = None
        self._self_timer = 40.0
        self._self_failures = 0

        self.stats = {"wood": 14, "stone": 6, "food": 22, "coin": 7}
        self.chronicle: list[dict] = []
        self.diaries: dict[str, str] = {}
        self.story_arc = {}
        self._story_pending = ""
        self._story_generation = 0
        self.day_number = 1
        self.current_day_key = self.clock.now.strftime("%Y-%m-%d")
        self.visitors: list[Visitor] = []
        self.dispatch_card: Visitor | None = None
        self.toasts: list[list] = []
        self.ambient_pending = 0
        self._social_generation = 0
        self._social_failures = 0
        self.script: list[tuple[Agent, str, float]] = []
        self._social_tracks = []
        self.social_timer = 12.0
        self.visitor_pending = False
        self.visitors_today = 0
        self.visitor_slots: list[int] = []
        self.visitor_slot_idx = 0
        self.night_demo_at = 0.0
        self._last_build_pct = -1
        self._last_condition = self.weather.condition
        self._autosave = 0.0
        self._diary_requested: set[str] = set()
        self._drag_last = (0, 0)
        self._dragging = False
        self._press_world = False
        self._was_live = self.clock.live

        self.news = NewsService(config, self.llm, self.i18n)
        self.alerts = AlertService(config, self.locations)
        self._alert_queue = []
        self._alert_retry_at = 0.0

        self._autoquit = float(os.environ.get("AIVILLAGE_AUTOQUIT", "0") or 0)
        self._autoshot = os.environ.get("AIVILLAGE_AUTOSHOT", "")
        self._shot_at = float(os.environ.get("AIVILLAGE_SHOT_AT", "2.0") or 2.0)
        self._shot_done = False
        self._started_at = time.time()

        self._plan_visitors()
        if not new_game:
            data, _ = load_slot(1)
            if data:
                self._apply_save(data)
                self.toast(self._saved_banner(data))
        if self.clock.now.hour >= 19:
            self.night_demo_at = time.time() + 90.0
