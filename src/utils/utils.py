from pathlib import Path

import pygame


def move_towards(current: float, target: float, dx: float):
    if current < target:
        return min(current + dx, target)
    return max(target, current - dx)


def load_image(path: Path, render_scale: float):
    assert path.exists() and path.suffix == ".png"
    assert render_scale > 0
    image = pygame.image.load(path)
    if render_scale:
        image = pygame.transform.scale_by(image, render_scale)
    return image
