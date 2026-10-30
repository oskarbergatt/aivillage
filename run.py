#!/usr/bin/env python
"""aivillage launcher.

    python run.py                 # live clock, live weather, your village
    python run.py --new           # start a fresh village (ignore the save)
    python run.py --lang de       # start in German
    python run.py --provider mock # offline demo model (no real dialogue quality)

Nothing here needs an API key to *open*: without a model the village still runs,
but conversations and dispatches stay quiet until one is configured.
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aivillage",
                                description="A small pixel village that lives on your clock.")
    p.add_argument("--new", action="store_true", help="ignore the save and start fresh")
    p.add_argument("--seed", type=int, default=None, help="world/roster seed")
    p.add_argument("--lang", choices=("en", "de"), default=None,
                   help="interface language for this run")
    p.add_argument("--provider", default=None,
                   choices=("auto", "ollama", "openai", "anthropic",
                            "openai_compatible", "mock", "none"),
                   help="force a language-model provider")
    p.add_argument("--model", default=None, help="model name for the chosen provider")
    p.add_argument("--config", default=None, help="path to an alternative config.toml")
    p.add_argument("--width", type=int, default=None, help="window width")
    p.add_argument("--height", type=int, default=None, help="window height")
    p.add_argument("--zoom", type=int, default=None, choices=(2, 3, 4, 5),
                   help="world zoom (integer pixel scale)")
    p.add_argument("--location", default=None,
                   help="override the detected city, e.g. --location Leipzig")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    from aivillage.config import Config, CONFIG_PATH
    from aivillage.app import VillageApp

    path = CONFIG_PATH
    if args.config:
        from pathlib import Path
        path = Path(args.config)
    try:
        config = Config(path)
    except Exception as exc:
        print(f"aivillage: bad config: {exc}", file=sys.stderr)
        return 2

    if args.lang:
        config.set("general.language", args.lang)
    if args.provider:
        config.set("llm.provider", args.provider)
    if args.model:
        config.set("llm.model", args.model)
    if args.width:
        config.set("general.window_width", args.width)
    if args.height:
        config.set("general.window_height", args.height)
    if args.zoom:
        config.set("general.zoom", args.zoom)

    try:
        app = VillageApp(config, new_game=args.new, seed=args.seed)
    except Exception as exc:
        print(f"aivillage: could not start: {exc}", file=sys.stderr)
        raise

    if args.location:
        found = app.locations.set_city(args.location)
        if found:
            app.weather_service.fetch()
            app.toast(f"{found.label}")
        else:
            app.toast(f"could not find {args.location}")

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
