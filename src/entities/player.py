import pygame
from pygame.surface import Surface
from tilemap_parser import ICollidableSprite

from src.entities.base import Character
from src.loader import SharedData


class Player(Character, ICollidableSprite):
    def __init__(
        self,
        x: float,
        y: float,
    ) -> None:
        animation_set = SharedData().state_animations["player"]
        collisoin_data = SharedData().character_collisions["player"]
        super().__init__(x, y, animation_set, collisoin_data, "idle")

        self.input_x = 0
        self.jump_pressed = False

    def get_state(self) -> str:
        if abs(self.vy) > 0.01:
            return "jump"
        if abs(self.vx) > 0.01:
            return "run"
        return "idle"

    def handle_key_input(self, dt: float):
        keys = pygame.key.get_pressed()
        self.input_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.jump_pressed = keys[pygame.K_SPACE]
        if self.input_x != 0:
            self.flipped = self.input_x < 0

    def update(self, dt: float):
        self.handle_key_input(dt)
        self.collision_runner.move_platformer(
            self, None, None, dt, input_x=self.input_x, jump_pressed=self.jump_pressed
        )
        return super().update(dt)

    def render(self, surface: Surface, offset: tuple[float, float]):
        return super().render(surface, offset)
