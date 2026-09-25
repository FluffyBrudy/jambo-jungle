from collections.abc import Callable
from random import choice, randint, random
from typing import Any

from tilemap_parser import CharacterCollision, ICollidable, ICollidableSprite, SpriteAnimationSet, get_shape_aabb

from src.entities.base import Character
from src.loader import SharedData
from src.settings import BULLET_CD

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
        target: ICollidable | ICollidableSprite,
        animaion_set: SpriteAnimationSet,
        collision_data: CharacterCollision,
        initial_state: str,
    ) -> None:
        super().__init__(x, y, animaion_set, collision_data, initial_state, "enemy")
        self.target = target


class Grunt(Enemy):
    def __init__(
        self,
        x: float,
        y: float,
        target: ICollidable | ICollidableSprite,
        spawn_bullet_cb: Callable[[float, float, str, int], Any],
    ) -> None:
        animation_set = SharedData().state_animations["grunt"]
        collisoin_data = SharedData().character_collisions["grunt"]
        super().__init__(x, y, target, animation_set, collisoin_data, "idle")

        self.is_shooting = False

        self.spawn_bullet_cb = spawn_bullet_cb
        self.bullet_cd = 0
        self.walking = 0
        self.direction = choice([1, -1])
        self.flipped = self.direction < 0

    def handle_shooting(self, dt: float):
        if self.bullet_cd >= 0.01:
            self.bullet_cd = max(self.bullet_cd - dt, 0)
            return
        if self.current_state != "shoot":
            return
        self.vx = 0
        self.bullet_cd = BULLET_CD
        dir_x = -1 if self.flipped else 1
        l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
        x = l - 10 if self.flipped else r
        self.spawn_bullet_cb(x, (t + b) * 0.5, "enemy", dir_x)

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
        if abs(self.target.x - self.x) <= 300 and abs(self.y - self.target.y) <= self.collision_shape.height:
            return "shoot"
        if abs(self.vx) > 0.01:
            return "run"
        return "idle"

    def update(self, dt: float):
        super().update(dt)
        if self.current_state != "shoot":
            self.handle_movement(dt)
        self.handle_shooting(dt)
        self.collision_runner.move_grounded(self, None, None, dt, one_way="directional")

        new_flip = self.direction < 0
        if self.current_state == "shoot":
            new_flip = (self.target.x - self.x) < 0
            self.direction = -1 if new_flip else 1
        if self.flipped != new_flip:
            self.flipped = new_flip
            self.flip_character_shape()
