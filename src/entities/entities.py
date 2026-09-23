from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

import pygame
from tilemap_parser import (
    AnimationPlayer,
    CapsuleShape,
    CircleShape,
    CollisionPolygon,
    CollisionRunner,
    ICollidableSprite,
    RectangleShape,
    SpriteAnimationSet,
    get_shape_aabb,
)

from src.core.asset_cache import get_animation_set, get_character_collision
from src.settings import ROOT_PATH


class IEntity(ABC):
    x: float
    y: float
    flipped: bool = False
    animation_spritesheet: SpriteAnimationSet
    animation_ms: float = 1000
    animation_state: dict[str, AnimationPlayer]
    current_state: str = ""
    blend_flag: int = 0
    shape_aabb: tuple[float, float, float, float]
    collision_shape: CircleShape | RectangleShape | CapsuleShape
    collision_mask: int = 0
    collision_layer: int = 0


class Entity(IEntity):
    render_scale = 1.0
    collision_runner: CollisionRunner = None  # pyright: ignore
    base_animation_ms: float = 1000.0

    def __new__(cls, *args, **kwargs) -> Self:
        if cls.collision_runner is None:
            raise ValueError("Collision runner is required to be initialized")
        return super().__new__(cls)

    def __init__(self, collision_path: Path, animation_path: Path) -> None:
        if not animation_path.exists():
            raise FileNotFoundError("animation path not found")
        if not collision_path.exists():
            raise FileNotFoundError("collision path not found")

        collision = get_character_collision(collision_path, render_scale=self.__class__.render_scale)
        if collision is None:
            raise ValueError("collision shape not found")
        if isinstance(collision.shape, (CircleShape, RectangleShape, CapsuleShape)):
            self.collision_shape = collision.shape
        else:
            raise TypeError("Only rectangle, capsule and circle shape is supported for entity")

        self.collision_mask = collision.collision_mask
        self.collision_layer = collision.collision_layer

        self.animation_spritesheet = get_animation_set(animation_path, render_scale=self.__class__.render_scale)
        keys = self.animation_spritesheet.library.animations.keys()
        self.animation_state = {key: AnimationPlayer(self.animation_spritesheet, key) for key in keys}
        self.shape_aabb = get_shape_aabb(self.x, self.y, self.collision_shape)

    @abstractmethod
    def get_state(self):
        raise NotImplementedError

    @abstractmethod
    def update_physics(self, dt: float):
        raise NotImplementedError

    def update(self, dt: float):
        self.update_physics(dt)
        self.update_animation(dt)
        self.shape_aabb = get_shape_aabb(self.x, self.y, self.collision_shape)

    def update_animation(self, dt: float):
        state = self.get_state()
        if state != self.current_state:
            self.animation_state[state].reset()
            self.current_state = state
            anim_clip = self.animation_spritesheet.library.animations.get(state)
            if anim_clip is not None:
                fps = float(getattr(anim_clip, "fps", 60.0))
                self.animation_ms = (fps / 60.0) * self.base_animation_ms
        curr_anim_state = self.animation_state[self.current_state]
        curr_anim_state.update(dt * self.animation_ms)

    def render(self, screen: pygame.Surface, offset: tuple[float, float]):
        current_image = self.animation_state[self.current_state].get_current_image()
        if current_image is None:
            return

        if self.flipped:
            current_image = pygame.transform.flip(current_image, True, False)

        screen.blit(
            current_image,
            (self.x - offset[0], self.y - offset[1]),
            special_flags=self.blend_flag,
        )
