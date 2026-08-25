import pygame
from tilemap_parser import ICollidableSprite, load_character_collision

from src.entities.entities import Entity, IEntity
from src.settings import ROOT_PATH


class Player(Entity, ICollidableSprite):
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        super().__init__(
            ROOT_PATH / "data" / "character_collision" / "player.collision.json",
            ROOT_PATH / "data" / "animations" / "player.anim.json",
        )
        self.current_state = self.get_state()
        self.flipped = False

        self.input_x = 0
        self.jump_pressed = False

    def get_state(self):
        if not self.on_ground:
            return "jump"
        if abs(self.vx) > 0.001:
            return "run"
        return "idle"

    def update_physics(self, dt):
        self.handle_movement()
        self.collision_result = self.collision_runner.move_platformer(
            self, None, None, dt, self.input_x, self.jump_pressed
        )

    def handle_movement(self):
        if self.jump_pressed:
            self.jump_pressed = False
        keys = pygame.key.get_pressed()
        input_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        if keys[pygame.K_SPACE]:
            self.jump_pressed = True
        if input_x != 0:
            self.flipped = input_x < 0
        self.input_x = input_x
