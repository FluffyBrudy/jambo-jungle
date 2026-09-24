from typing import TYPE_CHECKING

import pygame
from tilemap_parser import (
    CollisionRunner,
    ObjectCollisionManager,
    PhysicsWorld,
    TileLayerRenderer,
    describe_character_collision,
    describe_sprite,
    load_map,
)

from src.entities.base import Character
from src.entities.player import Player
from src.loader import LevelData, SharedData
from src.projectile.bullet import WeaponBullet
from src.settings import PROJECT_PATH
from src.types import Killable, WorldObject

if TYPE_CHECKING:
    from src.game import Game


class World:
    def __init__(self, game: "Game") -> None:
        self.game = game
        self.screen = self.game.screen

    def load_level(self, level: str):
        mapdata = load_map(PROJECT_PATH / "data" / "maps" / f"{level}.json", offset_x=0, offset_y=10)
        SharedData().preload(mapdata)
        LevelData().preload(mapdata)

        tileset_collision = SharedData().tileset_collision["default"]
        self.physics_world = PhysicsWorld.from_map(
            mapdata,
            tileset_collision,
            use_gids=True,
            exclude_layers={"entities"},
        )
        self.collision_runner = CollisionRunner.from_world(self.physics_world)

        self.tile_renderer = TileLayerRenderer(mapdata)
        self.objects_before_tiles = LevelData().objects_before_tiles
        self.objects_after_tiles = LevelData().objects_after_tiles

        Character.collision_runner = self.collision_runner
        self.player = Player(*LevelData().player_pos, self.spawn_bullet)

        self.obj_collision_manager = ObjectCollisionManager()
        self.object_container: list[WorldObject] = []

    def spawn_bullet(self, x: float, y: float, btype: str, direction: int):
        bullet = WeaponBullet(x, y, btype, direction)
        self.object_container.append(bullet)
        self.obj_collision_manager.add_object(bullet)

    def update(self, dt: float):
        self.player.update(dt)
        for i in range(len(self.object_container) - 1, -1, -1):
            obj = self.object_container[i]
            obj.update(dt)
            if isinstance(obj, Killable) and obj.can_kill():
                del self.object_container[i]
                self.obj_collision_manager.remove_object(obj)

    def render(self):
        for surf, x, y in self.objects_before_tiles:
            self.screen.blit(surf, (x - 0, y - 0))
        self.tile_renderer.render(self.screen, (0, 0))
        for surf, x, y in self.objects_after_tiles:
            self.screen.blit(surf, (x - 0, y - 0))
        for obj in self.object_container:
            obj.render(self.screen, (0, 0))
        self.player.render(self.screen, (0, 0))
        data = describe_sprite(self.player)
        for s in data:
            l, t, w, h = s["rect"]
            pygame.draw.rect(self.screen, "red", (l - 0, t - 0, w, h), 1)
