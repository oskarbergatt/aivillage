"""Public facade and controller composition."""
from __future__ import annotations

from collections import OrderedDict

from .client_shared import (
    Any,
    Callable,
    Config,
    DATA_DIR,
    Job,
    Path,
    Stats,
    _ANSI,
    claude_command,
    codex_command,
    dataclass,
    env,
    field,
    hashlib,
    json,
    os,
    parse_claude_output,
    parse_codex_output,
    queue,
    re,
    requests,
    shutil,
    spawn_command,
    strip_ansi,
    subprocess,
    tempfile,
    threading,
    time,
)

from .client_worker import ClientWorkerMixin
from .client_providers import ClientProvidersMixin


class LLMClient(ClientWorkerMixin, ClientProvidersMixin):
    def __init__(self, config: Config):
        self.config = config
        self.provider = "none"
        self.model = ""
        self.api_key = ""
        self.base_url = ""
        self.cli_path = ""
        self.available = False
        self.status = "not checked"
        self.stats = Stats()
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._cache_lock = threading.RLock()
        self._jobs: queue.Queue[Job] = queue.Queue()
        self._ambient_jobs: queue.Queue[Job] = queue.Queue()
        self._results: queue.Queue[tuple[Job, dict | None, str]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._ambient_worker: threading.Thread | None = None
        self._ambient_workers: list[threading.Thread] = []
        self._stop = threading.Event()
        self._resolve()
        self._start()


_ACTIVE: LLMClient | None = None


def client(config: Config) -> LLMClient:
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = LLMClient(config)
    return _ACTIVE
