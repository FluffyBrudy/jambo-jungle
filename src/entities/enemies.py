from collections.abc import Callable
from math import atan2, cos, cosh, degrees, pi, radians, sin
from random import choice, randint, random
from typing import Any, ClassVar

from tilemap_parser import CharacterCollision, ICollidable, ICollidableSprite, SpriteAnimationSet, get_shape_aabb

from src.entities.base import Character
from src.loader import SharedData
from src.settings import BULLET_CD, DEFAULT_HIT_CD
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

    def can_hit(self):
        return self.hit_cd == 0

    def can_kill(self):
        return self.current_state == "death" and self.animations[self.current_state].finished

    def trigger_hit_effect(self):
        self.hit_cd = DEFAULT_HIT_CD * 2
        self.flicker = True
        self.hit_count += 1
        if self.hit_count == GRUNT_MAX_HIT_COUNT:
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
    DIRECTION_LOOKUP: ClassVar[dict[float, str]] = {
        0.0: "east",
        45.0: "south_east",
        90.0: "south",
        135.0: "south_west",
        180.0: "west",
        -135.0: "north_west",
        -90.0: "north",
        -45.0: "north_east",
    }
    DIRECTION_VELOCITY: ClassVar[dict[float, tuple[float, float]]] = {
        0.0: (700, 0),
        45.0: (495, 495),
        90.0: (0, 700),
        135.0: (-495, 495),
        180.0: (-700, 0),
        -135.0: (-495, -495),
        -90.0: (0, -700),
        -45.0: (495, -495),
    }
    SPAWN_ANCHORS: ClassVar[dict[str, tuple[float, float]]] = {
        "north": (0.5, 0.0),
        "south": (0.5, 1.0),
        "east": (1.0, 0.5),
        "west": (0.0, 0.5),
        "north_east": (1.0, 0.0),
        "south_east": (1.0, 1.0),
        "north_west": (0.0, 0.0),
        "south_west": (0.0, 1.0),
    }

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
    def get_angle_deg(cls, angle_deg: float) -> float:
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

        fx, fy = self.SPAWN_ANCHORS[self.current_state]
        x = cx + (fx - 0.5) * wx
        y = cy + (fy - 0.5) * hy
        self.spawn_bullet_cb(x, y, "enemy", 0, self.DIRECTION_VELOCITY[self.get_angle_deg(degrees(radian))])

    def get_state(self) -> str:
        dy = self.target.y - self.y
        dx = self.target.x - self.x
        ang_deg = degrees(atan2(dy, dx))
        quantized_angle = self.get_angle_deg(ang_deg)
        return self.DIRECTION_LOOKUP.get(quantized_angle, "east")

    def can_hit(self):
        return False

    def trigger_hit_effect(self):
        return

    def update(self, dt: float):
        super().update(dt)
        self.handle_shooting(dt)
