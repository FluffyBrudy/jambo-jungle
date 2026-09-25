from typing import TYPE_CHECKING

import pygame
from tilemap_parser import (
    Camera,
    CollisionRunner,
    ICollidable,
    ObjectCollisionManager,
    PhysicsWorld,
    TileLayerRenderer,
    describe_character_collision,
    describe_sprite,
    get_shape_aabb,
    load_map,
)

from src.entities.base import Character
from src.entities.enemies import Enemy, Grunt
from src.entities.player import Player
from src.loader import LevelData, SharedData
from src.projectile import bullet
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
        mapdata = load_map(PROJECT_PATH / "data" / "maps" / f"{level}.json", offset_x=0, offset_y=5)
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
        Enemy.solid_tile_at = self.check_solid_tile_at
        self.player = Player(*LevelData().player_pos, self.spawn_bullet)
        self.camera = Camera(self.game.screen.width, self.game.screen.height, mode="deadzone")
        self.camera.follow(self.player)
        self.camera.set_bounds_from_map(mapdata)

        self.obj_collision_manager = ObjectCollisionManager()
        self.object_container: list[WorldObject] = []

        self.obj_collision_manager.add_object(self.player)
        for k, v in LevelData().enemies.items():
            for pos in v:
                if k == "grunt":
                    grunt = Grunt(*pos, self.player, self.spawn_bullet)
                    self.object_container.append(grunt)
                    self.obj_collision_manager.add_object(grunt)

    def check_solid_tile_at(self, sprite: ICollidable, x: float, y: float, direction: float):
        l, _, r, b = get_shape_aabb(x, y, sprite.collision_shape)
        probe_x, probe_y = (l - 2 if direction < 0 else r + 2, b + 2)
        tile_x, tile_y = self.collision_runner.get_tile_at(probe_x, probe_y)
        return self.physics_world.cell_has_collision((tile_x, tile_y))

    def spawn_bullet(self, x: float, y: float, btype: str, direction: int):
        bullet = WeaponBullet(x, y, btype, direction)
        self.object_container.append(bullet)
        self.obj_collision_manager.add_object(bullet)

    def update(self, dt: float):
        self.player.update(dt)
        self.camera.update(dt)
        for i in range(len(self.object_container) - 1, -1, -1):
            obj = self.object_container[i]

            obj.update(dt)
            if isinstance(obj, Killable) and obj.can_kill():
                del self.object_container[i]
                self.obj_collision_manager.remove_object(obj)

        for collision_result in self.obj_collision_manager.check_all_collisions():
            other = collision_result.other(self.player)
            if isinstance(other, WeaponBullet):
                other.is_dead = True

    def render(self):
        cam_x, cam_y = self.camera.offset

        for surf, x, y in self.objects_before_tiles:
            self.screen.blit(surf, (x - cam_x, y - cam_y))
        self.tile_renderer.render(self.screen, (cam_x, cam_y))
        for obj in self.object_container:
            obj.render(self.screen, (cam_x, cam_y))
        self.player.render(self.screen, (cam_x, cam_y))
        for surf, x, y in self.objects_after_tiles:
            self.screen.blit(surf, (x - cam_x, y - cam_y))

        data = describe_sprite(self.player)
        for s in data:
            l, t, w, h = s["rect"]  # pyright: ignore
            pygame.draw.rect(self.screen, "red", (l - cam_x, t - cam_y, w, h), 1)
