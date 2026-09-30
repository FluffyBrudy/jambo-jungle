from collections.abc import Callable
from math import atan2, cos, cosh, degrees, pi, radians, sin
from random import choice, randint, random
from typing import Any, ClassVar

from pygame import Rect, Surface
from tilemap_parser import (
    CharacterCollision,
    ICollidable,
    ICollidableSprite,
    RectangleShape,
    SpriteAnimationSet,
    get_shape_aabb,
)

from src.entities.base import Character
from src.loader import SharedData
from src.settings import BULLET_CD, DEFAULT_HIT_CD, DIRECTION_LOOKUP, DIRECTION_VELOCITY, SPAWN_ANCHORS
from src.types import Hitable, TSpawnBulletCb

WALK_COUNT = 250


class Enemy(Character, ICollidableSprite):
    solid_tile_at: Callable[[ICollidable, float, float, float], bool] = None  # pyright: ignore

    def __new__(cls, *args, **kwargs):
        if cls.solid_tile_at is None:
            raise ValueError("solid_tile_at is not implemented as look ahead for tile")
        return super().__new__(cls)

    def __init__(
        self,
        x: float,
        y: float,
        target: Hitable,
        animaion_set: SpriteAnimationSet,
        collision_data: CharacterCollision,
        initial_state: str,
    ) -> None:
        super().__init__(x, y, animaion_set, collision_data, initial_state, "enemy")
        self.target = target


GRUNT_MAX_HIT_COUNT = 3


class Grunt(Enemy):
    def __init__(
        self,
        x: float,
        y: float,
        target: Hitable,
        spawn_bullet_cb: TSpawnBulletCb,
    ) -> None:

        animation_set = SharedData().state_animations["grunt"]
        collisoin_data = SharedData().character_collisions["grunt"]
        super().__init__(x, y, target, animation_set, collisoin_data, "idle")
        if not isinstance(self.target, Hitable):
            raise TypeError("Target has to be hitable")

        self.is_shooting = False

        self.spawn_bullet_cb = spawn_bullet_cb
        self.bullet_cd = 0
        self.walking = 0
        self.direction = choice([1, -1])
        self.flipped = self.direction < 0
        self.hit_cd = 0
        self.hit_count = 0

        self.is_dead = False

    def can_hit(self):
        return self.hit_cd == 0

    def can_kill(self):
        return self.current_state == "death" and self.animations[self.current_state].finished

    def trigger_hit_effect(self, full: bool = False):
        self.hit_cd = DEFAULT_HIT_CD * 2
        self.flicker = True
        self.hit_count += 1 if not full else (GRUNT_MAX_HIT_COUNT + 1)
        if self.hit_count > GRUNT_MAX_HIT_COUNT and not self.is_dead:
            self.flicker = False
            self.is_dead = True
            SharedData().soundmanager.play("explosion_ground", "sfx")

    def handle_shooting(self, dt: float):
        if self.bullet_cd >= 0.01:
            self.bullet_cd = max(self.bullet_cd - dt, 0)
            return
        if not self.target.can_hit():
            return
        if self.current_state != "shoot":
            return
        self.vx = 0
        self.bullet_cd = BULLET_CD
        dir_x = -1 if self.flipped else 1
        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        x = l - 10 if self.flipped else r
        self.spawn_bullet_cb(x, (t + b) * 0.5, "enemy", dir_x, None)

    def handle_movement(self, dt: float):
        self.walking = max(0, self.walking - 1)
        if self.walking == 0:
            if random() < 0.01:
                self.walking = randint(int(WALK_COUNT * 0.2), WALK_COUNT)
                self.direction *= -1
                self.vx = self.direction * 100
            else:
                self.vx = 0
        elif self.on_ground and self.vx != 0 and not self.solid_tile_at(self, self.x, self.y, self.direction):
            if self.solid_tile_at(self, self.x, self.y, -self.direction):
                self.direction *= -1
                self.vx = self.direction * 100
            else:
                self.vx = 0

    def get_state(self) -> str:
        if self.hit_count >= GRUNT_MAX_HIT_COUNT:
            return "death"
        if self.hit_cd > 0.01:
            return "hurt"
        if (
            self.target.can_hit()
            and abs(self.target.x - self.x) <= 300
            and abs(self.y - self.target.y) <= self.collision_shape.height
        ):
            return "shoot"
        if abs(self.vx) > 0.01:
            return "run"
        return "idle"

    def update(self, dt: float):
        super().update(dt)
        if self.current_state != "shoot":
            self.handle_movement(dt)
        self.handle_shooting(dt)

        new_flip = self.direction < 0
        if self.current_state == "shoot":
            new_flip = (self.target.x - self.x) < 0
            self.direction = -1 if new_flip else 1
        if self.flipped != new_flip:
            self.flipped = new_flip
            self.flip_character_shape()

        if self.hit_cd != 0:
            self.vx = 0
            self.hit_cd = max(self.hit_cd - dt, 0)
            if self.hit_cd == 0:
                self.flicker = False
        self.collision_runner.move_grounded(self, None, None, dt, one_way="directional")


class WallTurret(Enemy):
    def __init__(
        self,
        x: float,
        y: float,
        target: Hitable,
        spawn_bullet_cb: TSpawnBulletCb,
    ) -> None:
        animation_set = SharedData().state_animations["turret"]
        collisoin_data = SharedData().character_collisions["turret"]
        super().__init__(x, y, target, animation_set, collisoin_data, "east")
        self.spawn_bullet_cb = spawn_bullet_cb

        self.bullet_cd = 0

    @classmethod
    def get_quantized_ang(cls, angle_deg: float) -> float:
        normalized = (angle_deg + 180) % 360 - 180

        quantized_angle = round(normalized / 45.0) * 45.0

        if quantized_angle == -180.0:
            quantized_angle = 180.0

        return quantized_angle

    def handle_shooting(self, dt: float):
        if self.bullet_cd > 0.01:
            self.bullet_cd = max(self.bullet_cd - dt, 0)
            return
        if ((self.target.x - self.x) ** 2 + (self.target.y - self.y) ** 2) > 90000:
            return
        self.bullet_cd = BULLET_CD
        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        dy = self.target.y - self.y
        dx = self.target.x - self.x
        radian = atan2(dy, dx)

        cx, cy = (l + r) * 0.5, (t + b) * 0.5
        wx, hy = r - l, b - t

        fx, fy = SPAWN_ANCHORS[self.current_state]
        x = cx + (fx - 0.5) * wx
        y = cy + (fy - 0.5) * hy
        speed = DIRECTION_VELOCITY[self.get_quantized_ang(degrees(radian))]
        self.spawn_bullet_cb(x, y, "enemy", 0, (speed[0] * 0.5, speed[1] * 0.5))

    def get_state(self) -> str:
        dy = self.target.y - self.y
        dx = self.target.x - self.x
        ang_deg = degrees(atan2(dy, dx))
        quantized_angle = self.get_quantized_ang(ang_deg)
        return DIRECTION_LOOKUP.get(quantized_angle, "east")

    def can_hit(self):
        return False

    def trigger_hit_effect(self):
        return

    def update(self, dt: float):
        super().update(dt)
        self.handle_shooting(dt)


class GruntSpawnPortal:
    def __init__(self, area: Rect, cleanup_cb: Callable) -> None:
        collision_data = SharedData().character_collisions["grunt_portal"]
        self.cleanup_cb = cleanup_cb
        self.broken = False
        self.surface = SharedData().images["grunt_portal"]
        self.collision_shape = RectangleShape(*self.surface.size)
        self.collision_layer = collision_data.collision_layer
        self.collision_mask = collision_data.collision_mask
        self.hit_count = 0
        self.hit_cd = 0
        self.death_after = 0

        x, y = area.midbottom
        l, _, r, b = get_shape_aabb(0, 0, self.collision_shape)
        self.x = x - (r - l) * 0.5
        self.y = y - b

    def update(self, dt: float):
        if self.hit_cd > 0.01:
            self.hit_cd = max(self.hit_cd - dt, 0)
        if self.death_after > 0:
            self.death_after = max(self.death_after - dt, 0)

    def can_hit(self):
        return self.hit_cd == 0 and not self.broken

    def trigger_hit_effect(self, full: bool = False):
        self.hit_count += 1 if not full else (GRUNT_MAX_HIT_COUNT + 1)
        if self.hit_count > GRUNT_MAX_HIT_COUNT * 5 and not self.broken:
            self.broken = True
            self.surface = SharedData().images["grunt_portal_broke"]
            self.death_after = 5
            self.cleanup_cb()

    def can_kill(self):
        return self.broken and self.death_after == 0

    def render(self, surface: Surface, offset: tuple[float, float]):
        surface.blit(self.surface, (self.x - offset[0], self.y - offset[1]))
