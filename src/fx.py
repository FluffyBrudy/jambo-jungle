from math import sin

import pygame
from pygame.math import lerp
from pygame.surface import Surface


def apply_flicker(surface: Surface) -> Surface:
    alpha = lerp(0.2, 1, sin(pygame.time.get_ticks() * 20), True)
    surface_cp = surface.copy()
    surface_cp.set_alpha(int(alpha * 255))
    mask = pygame.mask.from_surface(surface_cp)
    outlines = mask.outline()
    pygame.draw.lines(surface_cp, (255, 0, 0), True, outlines, width=5)
    return surface_cp
