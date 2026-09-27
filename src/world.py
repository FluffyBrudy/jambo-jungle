from random import random
from typing import TYPE_CHECKING

import pygame
from pygame.rect import Rect
from tilemap_parser import (
    Camera,
    CollisionRunner,
    ICollidable,
    ObjectCollisionManager,
    PhysicsWorld,
    TileLayerRenderer,
    describe_sprite,
    describe_tile_layer,
    get_shape_aabb,
    load_map,
)

from src.entities.base import Character
from src.entities.collision_resolver import resolve_collision
from src.entities.enemies import Enemy, Grunt, GruntSpawnPortal, WallTurret
from src.entities.player import Player
from src.loader import LevelData, SharedData
from src.objects.barrel import BarrelRed
from src.projectile.bullet import WeaponBullet
from src.settings import PROJECT_PATH
from src.types import Killable, WorldObject

if TYPE_CHECKING:
    from src.game import Game


class World:
    def __init__(self, game: "Game") -> None:
        self.game = game
        self.screen = self.game.screen

        self.grunt_spawn_queue: list[tuple[float, float]] = []

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
        self._tile_polys = describe_tile_layer(self.physics_world.tile_map, world=self.physics_world)

        self.tile_renderer = TileLayerRenderer(mapdata)
        self.objects_before_tiles = LevelData().objects_before_tiles
        self.objects_after_tiles = LevelData().objects_after_tiles
        self.grunt_spawn_nodes = LevelData().grunt_spawner_nodes

        Character.collision_runner = self.collision_runner
        Enemy.solid_tile_at = self.check_solid_tile_at
        self.player = Player(*LevelData().player_pos, self.spawn_bullet)
        self.camera = Camera(self.game.screen.width, self.game.screen.height, mode="deadzone")
        self.camera.follow(self.player)
        self.camera.set_bounds_from_map(mapdata)

        self.obj_collision_manager = ObjectCollisionManager()
        self.object_container: list[WorldObject] = []

        self.obj_collision_manager.add_object(self.player)
        for area in self.grunt_spawn_nodes:
            grunt_portal = GruntSpawnPortal(area, self._remove_grunt_spawn_node(area))
            self.object_container.append(grunt_portal)  # pyright: ignore
            self.obj_collision_manager.add_object(grunt_portal)  # pyright: ignore

        for barrel_type, positions in LevelData().barrels.items():
            for pos in positions:
                if barrel_type == "red":
                    barrel = BarrelRed(*pos)
                    self.object_container.append(barrel)
                    self.obj_collision_manager.add_object(barrel)

        for k, v in LevelData().enemies.items():
            for pos in v:
                if k == "grunt":
                    grunt = Grunt(*pos, self.player, self.spawn_bullet)  # pyright: ignore
                    self.object_container.append(grunt)
                    self.obj_collision_manager.add_object(grunt)
                elif k == "turret":
                    grunt = WallTurret(*pos, self.player, self.spawn_bullet)  # pyright: ignore
                    self.object_container.append(grunt)
                    self.obj_collision_manager.add_object(grunt)

        self.soundmanager = SharedData().soundmanager
        self.soundmanager.play("main", "main")

    def _remove_grunt_spawn_node(self, node: Rect):
        def cleanup():
            print(self.grunt_spawn_nodes)
            self.grunt_spawn_nodes.remove(node)

        return cleanup

    def spawn_grunt_from_portal(self, pos: tuple[float, float]):
        if self.grunt_spawn_nodes.__len__() == 0:
            return
        x, y = pos
        min_node = min(self.grunt_spawn_nodes, key=lambda rect: (rect.x - x) ** 2 + (rect.y - y) ** 2)
        grunt = Grunt(*min_node.topleft, self.player, self.spawn_bullet)  # pyright: ignore
        self.object_container.append(grunt)
        self.obj_collision_manager.add_object(grunt)

    def check_solid_tile_at(self, sprite: ICollidable, x: float, y: float, direction: float):
        l, _, r, b = get_shape_aabb(x, y, sprite.collision_shape)
        probe_x, probe_y = (l - 2 if direction < 0 else r + 2, b + 2)
        tile_x, tile_y = self.collision_runner.get_tile_at(probe_x, probe_y)
        return self.physics_world.cell_has_collision((tile_x, tile_y))

    def spawn_bullet(self, x: float, y: float, btype: str, direction: int, speed: tuple[float, float] | None = None):
        bullet = WeaponBullet(x, y, btype, direction, speed)
        self.object_container.append(bullet)
        self.obj_collision_manager.add_object(bullet)
        self.soundmanager.play("shoot", "sfx")

    def update(self, dt: float):
        self.player.update(dt)
        self.camera.update(dt)
        for i in range(len(self.object_container) - 1, -1, -1):
            obj = self.object_container[i]

            obj.update(dt)
            if isinstance(obj, Killable) and obj.can_kill():
                if isinstance(obj, Grunt) and len(self.grunt_spawn_nodes) != 0:
                    self.grunt_spawn_queue.append((obj.x, obj.y))
                del self.object_container[i]
                self.obj_collision_manager.remove_object(obj)

        for collision_result in self.obj_collision_manager.check_all_collisions():
            resolve_collision(collision_result)

        if len(self.grunt_spawn_queue) != 0:
            if random() < 0.01:
                self.spawn_grunt_from_portal(self.grunt_spawn_queue.pop())

    def render(self):
        cam_x, cam_y = self.camera.offset

        for surf, x, y in self.objects_before_tiles:
            self.screen.blit(surf, (x - cam_x, y - cam_y))
        self.tile_renderer.render(self.screen, (cam_x, cam_y))
        for obj in self.object_container:
            obj.render(self.screen, (cam_x, cam_y))
            # self._debug_obj(obj, cam_x, cam_y)
        self.player.render(self.screen, (cam_x, cam_y))
        for surf, x, y in self.objects_after_tiles:
            self.screen.blit(surf, (x - cam_x, y - cam_y))

        # self._debug_obj(self.player, cam_x, cam_y)
        # self._debug_tileset(cam_x, cam_y)

    def _debug_obj(self, obj, cam_x, cam_y, /):
        data = describe_sprite(obj)
        for s in data:
            if s.get("rect"):
                l, t, w, h = s["rect"]  # pyright: ignore
                pygame.draw.rect(self.screen, "red", (l - cam_x, t - cam_y, w, h), width=5)
            elif s.get("circle"):
                x, y, radius = s["circle"]  # pyright: ignore
                pygame.draw.circle(self.screen, "blue", (x - cam_x, y - cam_y), radius, width=5)

    def _debug_tileset(self, cam_x: float, cam_y: float):
        for p in self._tile_polys:
            color = "yellow" if p["one_way"] else "red"
            pygame.draw.polygon(
                self.screen,
                color,
                [(x - cam_x, y - cam_y) for x, y in p["points"]],  # pyright: ignore
                1,  # pyright: ignore
            )
