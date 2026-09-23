from typing import override

import pygame
from tilemap_parser import ICollidableSprite

from src.entities.entities import Entity, IEntity
from src.projectile.bullet import BulletSpark, SimpleAnimatedBullet
from src.settings import ROOT_PATH
from src.utils.math import move_towards

RUN_SPEED = 150.0
# NOTE: ground start 2200 vs stop 1100 changes feel vs old 1500/1500 — intentional tuning
GROUND_ACCELERATION = 2200
GROUND_DECCELERATION = 1100
AIR_ACCELERATION = 1100
MAX_FALL_SPEED = 800
JUMP_STRENGTH = -420  # keep legacy typo alias for compatibility
JUMP_STRENGHT = JUMP_STRENGTH
GRAVITY = 1000
BULLET_COOLDOWN = 0.15


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
        self.input_x = 0
        self.jump_pressed = False
        self.is_attacking = False
        self.flipped = False

        self.current_state = self.get_state()

        self.bullet_cooldown = 0

    def get_state(self):
        if not self.on_ground:
            return "jump"
        if self.is_attacking:
            if abs(self.vx) > 0.001:
                return "run_shoot"
            return "shoot"
        elif abs(self.vx) > 0.001:
            return "run"
        return "idle"

    def update_physics(self, dt):
        self.handle_movement()

        max_vx = self.input_x * RUN_SPEED
        self.vy = min(self.vy + GRAVITY * dt, MAX_FALL_SPEED)
        if self.jump_pressed:
            self.vy = JUMP_STRENGHT
        if self.input_x != 0:
            accl = GROUND_ACCELERATION if self.on_ground else AIR_ACCELERATION
            self.vx = move_towards(self.vx, max_vx, dt * accl)
        else:
            decc = GROUND_DECCELERATION if self.on_ground else AIR_ACCELERATION
            self.vx = move_towards(self.vx, 0, dt * decc)

        self.collision_result = self.collision_runner.move_platformer(
            self, None, None, dt, self.input_x, self.jump_pressed, velocity=(self.vx, self.vy)
        )

    def handle_movement(self):
        keys = pygame.key.get_pressed()
        input_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        if keys[pygame.K_SPACE]:
            self.is_attacking = True
            if self.bullet_cooldown == 0:
                self.bullet_cooldown = BULLET_COOLDOWN
                x, y = self.shape_aabb[2 - 2 * self.flipped], (self.shape_aabb[1] + self.shape_aabb[3]) * 0.5
                dir = 1 - 2 * self.flipped
                SimpleAnimatedBullet.objects.add(
                    SimpleAnimatedBullet(x, y, (RUN_SPEED * dir + abs(self.vx) * dir, 0), "player_bullet")
                )
                BulletSpark.objects.add(BulletSpark())
        else:
            self.is_attacking = False
            BulletSpark.objects.clear()
        if keys[pygame.K_UP] and self.on_ground:
            self.jump_pressed = True
        else:
            self.jump_pressed = False

        self.input_x = input_x
        if input_x != 0:
            self.flipped = input_x < 0

    @override
    def update(self, dt: float):
        if self.bullet_cooldown > 0:
            self.bullet_cooldown = max(0, self.bullet_cooldown - dt)
        return super().update(dt)
