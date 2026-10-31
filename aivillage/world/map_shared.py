"""Village generation. Hand-placed landmarks, procedural edges."""
from __future__ import annotations

import math
import random

import pygame

from ..assets import sprites
from ..assets.palette import P
from .objects import BuildSite, CropPlot, Obj, make_house_obj

GRASS, PATH, PLAZA, WATER, SAND, SOIL = range(6)

W, H = 64, 48
TILE = 16


