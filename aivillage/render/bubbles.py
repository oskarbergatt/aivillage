"""Speech-bubble drawing for villagers and visitors."""
import pygame

from ..assets.font import get_font, render, wrap
from ..assets.palette import P


class BubbleRenderer:
    def _draw_bubble(self, screen, text: str, anchor: tuple[int, int],
                     colour=(240, 232, 210), pending: bool = False,
                     kind: str = "speech") -> None:
        size = 16
        font = get_font(size)
        max_w = 300 if screen.get_width() > 1000 else 220
        if pending:
            dots = "." * (1 + int(self._dots) % 3)
            lines = [dots]
        else:
            lines = wrap(text, size, max_w)[:5]
        if not lines:
            return
        line_h = font.get_height() + 3
        width = max(font.size(line)[0] for line in lines) + 18
        height = line_h * len(lines) + 12
        ax, ay = anchor
        x = max(8, min(screen.get_width() - width - 8, ax - width // 2))
        y = ay - height - 26
        flipped = False
        if y < 8:
            y = ay + 28
            flipped = True
        rect = pygame.Rect(x, y, width, height)
        shadow = rect.move(2, 2)
        pygame.draw.rect(screen, (16, 14, 24), shadow)
        pygame.draw.rect(screen, P["ui_bg"], rect)
        border = P["ui_cool"] if kind == "dispatch" else P["ui_line"]
        pygame.draw.rect(screen, border, rect, 1)
        pygame.draw.rect(screen, P["ui_bg2"], (rect.x + 2, rect.y + 2, rect.w - 4, 2))
        tail_x = max(rect.x + 12, min(rect.right - 12, ax))
        if flipped:
            pygame.draw.polygon(screen, border,
                                [(tail_x - 5, rect.top), (tail_x + 5, rect.top),
                                 (ax, rect.top - 9)])
        else:
            pygame.draw.polygon(screen, border,
                                [(tail_x - 5, rect.bottom - 1),
                                 (tail_x + 5, rect.bottom - 1),
                                 (ax, rect.bottom + 9)])
        for i, line in enumerate(lines):
            img = render(line, size, colour)
            screen.blit(img, (rect.x + 9, rect.y + 7 + i * line_h))
        if pending:
            self._dots += 0.12
