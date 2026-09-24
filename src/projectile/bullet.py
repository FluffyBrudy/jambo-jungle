import pygame
from pygame.surface import Surface
from tilemap_parser import AnimationPlayer, ICollidable, get_shape_aabb

from src.loader import SharedData


class WeaponBullet(ICollidable):
    def __init__(self, x: float, y: float, btype: str, direction: int) -> None:
        animation_sheet = SharedData().state_animations["weapon_bullets"]
        collision_data = SharedData().character_collisions["weapon_bullet"]
        self.animation = AnimationPlayer(animation_sheet, btype)
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer
        self.collision_shape = collision_data.shape

        _, t, _, b = get_shape_aabb(0, 0, self.collision_shape)
        self.x = x
        self.y = y - (b - t) // 2
        self.speed = direction * 700

    def can_kill(self):
        return self.animation.finished

    def update(self, dt: float):
        self.x += self.speed * dt
        self.animation.update(dt * 700)

    def render(self, surface: Surface, offset: tuple[float, float]):
        frame: Surface = self.animation.get_current_image()  # pyright: ignore
        if self.speed < 0:
            frame = pygame.transform.flip(frame, True, False)
        surface.blit(frame, (self.x - offset[1], self.y - offset[1]))
