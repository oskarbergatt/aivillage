"""aivillage — the running village.

One process, one window. The simulation ticks on real elapsed time; the clock
inside the village is the player's clock unless they fast-forward.
"""
from __future__ import annotations

import math
import os
import random
import threading
import time
import traceback
from datetime import datetime

import pygame

from .agents.brain import Agent
from .agents.jobs import JOBS, ADULT_JOBS, job_choices
from .agents.roster import ROSTER
from .agents.visitor import Visitor
from .assets import sprites
from .assets.palette import P
from .assets.sfx import Sfx
from .chat import ChatMixin, ChatState
from .i18n import I18N
from .llm import prompts
from .llm.client import client as make_llm
from .news.pipeline import NewsService
from .news.alerts import AlertService
from .news.courier import AlertCourierMixin
from .reality.clock import SimClock
from .reality.geo import LocationService
from .reality.weather import WeatherService
from .render.camera import Camera
from .render.renderer import Renderer
from .render.photo import PhotoExportMixin
from .render.ui import UI
from .save import save_village, load_slot, slot_path
from .voice.tts import VoiceService
from .world.mapgen import H, W, World

TILE = 16


