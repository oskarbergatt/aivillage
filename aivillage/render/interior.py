"""Cutaway house interior rendering."""
from __future__ import annotations

import pygame

from ..assets.font import render
from ..assets.palette import P


class InteriorRendererMixin:
    def draw_interior(self, screen: pygame.Surface, house, agents, i18n) -> None:
        """Draw an enterable cutaway room without changing world state."""
        w, h = screen.get_size()
        screen.fill((29, 25, 36))
        room = pygame.Rect(int(w * .16), int(h * .12), int(w * .68), int(h * .76))
        pygame.draw.rect(screen, (111, 76, 60), room)
        pygame.draw.rect(screen, (196, 151, 105), room.inflate(-12, -12))
        floor = pygame.Rect(room.x + 8, room.y + int(room.h * .57), room.w - 16, int(room.h * .39))
        pygame.draw.rect(screen, (137, 91, 62), floor)
        for x in range(floor.x, floor.right, 32):
            pygame.draw.line(screen, (116, 75, 55), (x, floor.y), (x, floor.bottom), 2)
        pygame.draw.rect(screen, (71, 115, 139), (room.x + 36, room.y + 36, 76, 56))
        pygame.draw.line(screen, (206, 190, 145), (room.x + 74, room.y + 36), (room.x + 74, room.y + 92), 4)
        pygame.draw.rect(screen, (91, 55, 43), (room.right - 118, room.y + 106, 76, 82))
        pygame.draw.rect(screen, (226, 128, 58), (room.right - 100, room.y + 142, 38, 44))
        pygame.draw.ellipse(screen, (101, 65, 47), (room.centerx - 90, floor.y + 40, 180, 74))
        pygame.draw.rect(screen, (151, 105, 72), (room.centerx - 10, floor.y + 75, 20, 54))
        pygame.draw.rect(screen, (90, 60, 65), (room.x + 34, floor.y + 48, 112, 74))
        pygame.draw.rect(screen, (208, 177, 143), (room.x + 34, floor.y + 48, 112, 18))
        name = house.data.get("name", house.kind) if house else "Home"
        title = render(i18n.t("interior.home_title", name=name.title()),
                       24, P["ui_accent"], P["ink"])
        screen.blit(title, title.get_rect(center=(w // 2, room.y - 20)))
        resident = next((a for a in agents if a.key == name), None)
        if resident:
            sprite = self._scaled_sprite(resident.sprite(), .9)
            screen.blit(sprite, sprite.get_rect(midbottom=(room.centerx, floor.bottom - 10)))
        hint = render(i18n.t("interior.leave_hint"), 16, P["ui_text"], P["ink"])
        screen.blit(hint, hint.get_rect(center=(w // 2, h - 22)))
