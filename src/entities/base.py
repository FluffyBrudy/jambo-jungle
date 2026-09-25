from math import sin
from typing import Unpack, cast

import pygame
from pygame.math import lerp
from pygame.surface import Surface
from tilemap_parser import (
    AnimationPlayer,
    CharacterCollision,
    CollisionRunner,
    SpriteAnimationSet,
    SpriteShape,
    flip_character_shape,
)

from src.fx import apply_flicker


class Character:
    collision_runner: CollisionRunner = None  # pyright:ignore

    def __new__(cls, *args, **kwargs):
        if cls.collision_runner is None:
            raise ValueError("Collision runner is required before instantiation")
        return super().__new__(cls)

    def __init__(
        self,
        x: float,
        y: float,
        animaion_set: SpriteAnimationSet,
        collision_data: CharacterCollision,
        initial_state: str,
        label: str,
    ) -> None:
        self.animations = {k: AnimationPlayer(animaion_set, k) for k in animaion_set.library.animations}
        self.collision_shape = cast(SpriteShape, collision_data.shape)
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer
        self.current_state = initial_state
        self.flipped = False
        self.vx = 0
        self.vy = 0
        self.x = x
        self.y = y
        self.on_ground = False

        self.fps = {k: (v.fps / 60) for k, v in animaion_set.library.animations.items()}
        self.label = label
        self.alpha = 255

        self.flicker = False

    def sync_state(self):
        new_state = self.get_state()
        if new_state != self.current_state:
            self.current_state = new_state
            self.animations[self.current_state].reset()

    def get_state(self) -> str:
        raise NotImplementedError

    def flip_character_shape(self):
        image: Surface = self.animations[self.current_state].get_current_image()  # pyright: ignore
        self.collision_shape = flip_character_shape(self.collision_shape, image.size)

    def update(self, dt: float):
        self.sync_state()
        scale = self.fps[self.current_state]
        self.animations[self.current_state].update(dt * 1000 * scale)

    def render(self, surface: Surface, offset: tuple[float, float]):
        image: Surface = self.animations[self.current_state].get_current_image()  # pyright:ignore

        if self.flipped:
            image = pygame.transform.flip(image, True, False)
        if self.flicker:
            image = apply_flicker(image)
        surface.blit(image, (self.x - offset[0], self.y - offset[1]))
