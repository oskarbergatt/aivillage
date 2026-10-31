"""Screenshot and postcard export from the current village view."""
from datetime import datetime
import traceback

import pygame

from ..assets.font import draw_text
from ..assets.palette import P
from ..config import DATA_DIR


class PhotoExportMixin:
    def _screenshot(self) -> None:
        try:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = DATA_DIR / f"aivillage-{stamp}.png"
            pygame.image.save(self.screen, str(path))
            self.toast(f"screenshot: {path.name}")
        except Exception:
            pass

    def _postcard(self) -> None:
        """Export the unobstructed view with a small dated postcard border."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            w, h = self.screen.get_size()
            card = pygame.Surface((w + 40, h + 90))
            card.fill(P["cream"])
            card.blit(self.screen, (20, 20))
            caption = f"{self.locations.location.label}  ·  {self.clock.date_text()}"
            draw_text(card, caption, (20, h + 43), 16, P["ink"])
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            pygame.image.save(card, str(DATA_DIR / f"postcard-{stamp}.png"))
        except Exception:
            traceback.print_exc()
