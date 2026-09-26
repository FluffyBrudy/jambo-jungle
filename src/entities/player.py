import pygame
from pygame.surface import Surface
from tilemap_parser import ICollidableSprite, get_shape_aabb

from src.entities.base import Character
from src.loader import SharedData
from src.settings import BULLET_CD, DEFAULT_HIT_CD
from src.types import TSpawnBulletCb


class Player(Character, ICollidableSprite):
    def __init__(
        self,
        x: float,
        y: float,
        spawn_bullet_cb: TSpawnBulletCb,
    ) -> None:
        animation_set = SharedData().state_animations["player"]
        collisoin_data = SharedData().character_collisions["player"]
        super().__init__(x, y, animation_set, collisoin_data, "idle", "player")

        self.input_x = 0
        self.jump_pressed = False
        self.shoot_pressed = False

        self.spawn_bullet_cb = spawn_bullet_cb
        self.bullet_cd = 0

        self.hit_cd = 0
        self.flicker = False

    def get_state(self) -> str:
        if self.hit_cd > 0.01:
            return "hurt"
        if abs(self.vy) > 0.01:
            return "jump"
        if abs(self.vx) > 0.01:
            if self.shoot_pressed:
                return "run_shoot"
            return "run"
        if self.shoot_pressed:
            return "shoot"
        return "idle"

    def can_hit(self):
        return self.hit_cd == 0

    def trigger_hit_effect(self):
        self.hit_cd = DEFAULT_HIT_CD * 3
        self.flicker = True
        self.vy = -400
        SharedData().soundmanager.play("hurt", "sfx")

    def handle_shooting(self, dt: float):
        if self.bullet_cd > 0.01:
            self.bullet_cd = max(self.bullet_cd - dt, 0)
        elif self.shoot_pressed:
            self.bullet_cd = BULLET_CD
            dir_x = -1 if self.flipped else 1
            l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
            x = l - 10 if self.flipped else r
            self.spawn_bullet_cb(x, (t + b) * 0.5, "player", dir_x, None)

    def handle_key_input(self, dt: float):
        keys = pygame.key.get_pressed()
        self.input_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.jump_pressed = keys[pygame.K_UP]
        self.shoot_pressed = keys[pygame.K_SPACE]

    def update(self, dt: float):
        self.handle_key_input(dt)
        self.handle_shooting(dt)
        if self.input_x != 0:
            new_flip = self.vx < 0
            if new_flip != self.flipped:
                self.flipped = new_flip
                # bug not worth the solve, when it overlap on x axis while on air, due to flip it forever stucks
                # to prevent it, the flipping is omitted when velocity is non zero, the 0.01 is just float safety
                if not abs(self.vy) > 0.01:
                    self.flip_character_shape()

        if self.hit_cd != 0:
            self.hit_cd = max(self.hit_cd - dt, 0)
            if self.hit_cd == 0:
                self.flicker = False

        was_on_ground = self.on_ground
        prev_vy = self.vy
        self.collision_runner.move_platformer(
            self, None, None, dt, input_x=self.input_x, jump_pressed=self.jump_pressed
        )
        just_jumped = was_on_ground and not self.on_ground and self.vy < 0
        just_fall = not was_on_ground and self.on_ground and prev_vy > 0
        if just_jumped:
            SharedData().soundmanager.play("jump", "sfx")
        elif just_fall:
            SharedData().soundmanager.play("land", "sfx")
        super().update(dt)

    def render(self, surface: Surface, offset: tuple[float, float]):
        return super().render(surface, offset)
