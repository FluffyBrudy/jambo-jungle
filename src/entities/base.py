from typing import cast

import pygame
from pygame.surface import Surface
from tilemap_parser import (
    AnimationPlayer,
    CharacterCollision,
    CollisionRunner,
    SpriteAnimationSet,
    SpriteShape,
    flip_character_shape,
)


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
    ) -> None:
        self.animations = {k: AnimationPlayer(animaion_set, k) for k in animaion_set.library.animations}
        self.collision_shape = cast(SpriteShape, collision_data.shape)
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer
        self.current_state = initial_state
        self.flipped = False
        self.vx = 0
        self.vy = 0
        self.x = 0
        self.y = 0
        self.on_ground = False

    def sync_state(self):
        new_state = self.get_state()
        if new_state != self.current_state:
            self.current_state = new_state
            self.animations[self.current_state].reset()

    def get_state(self) -> str:
        raise NotImplementedError

    def flip_character_shape(self):
        image: Surface = self.animations[self.current_state].get_current_image()  # pyright: ignore
        if self.flipped:
            self.collision_shape = flip_character_shape(self.collision_shape, image.size)
        else:
            self.collision_shape = self.collision_shape

    def update(self, dt: float):
        self.sync_state()
        self.animations[self.current_state].update(dt * 1000)

    def render(self, surface: Surface, offset: tuple[float, float]):
        image: Surface = self.animations[self.current_state].get_current_image()  # pyright:ignore

        if self.flipped:
            image = pygame.transform.flip(image, True, False)
        surface.blit(image, (self.x, self.y))
