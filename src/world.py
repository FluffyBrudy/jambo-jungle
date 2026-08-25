from typing import TYPE_CHECKING

from tilemap_parser import Camera, load_map, load_tileset_collision

from src.core.loader import WorldLoader
from src.entities.entities import Entity
from src.entities.player import Player
from src.settings import ROOT_PATH

if TYPE_CHECKING:
    from game import Game


class World:
    def __init__(self, game: "Game") -> None:
        self.game = game
        self.primary_surface = self.game.screen

        map_data = load_map(ROOT_PATH / "data" / "maps" / "0.json")

        tileset_collision = load_tileset_collision(ROOT_PATH / "data" / "collision" / "tileset.collision.json")
        if tileset_collision is None:
            raise ValueError("Tileset collision is null")
        self.world = WorldLoader(map_data, tileset_collision, exclude_layers={"sky"})
        self.static_objects, self.dynamic_obj = WorldLoader.load_objects(
            map_data,
            {"sky"},
            {"player", "clouds", "objprops"},
        )
        self.world_objects = self.dynamic_obj["objprops"]
        Entity.render_scale = map_data.render_scale
        Entity.collision_runner = self.world.collision_runner

        assert "player" in self.dynamic_obj

        player_pos = self.dynamic_obj["player"][0]
        self.player = Player(player_pos[1], player_pos[2])
        self.camera = Camera(*self.primary_surface.size, mode="deadzone")
        self.camera.follow(self.player)

    def update(self, dt: float):
        self.player.update(dt)
        self.camera.update(dt)

    def render(self):
        camx, camy = self.camera.offset
        for surf, x, y in self.static_objects:
            self.primary_surface.blit(surf, (x, y))
        for surf, x, y in self.world_objects:
            self.primary_surface.blit(surf, (x - camx, y - camy))
        self.world.tile_layer_renderer.render(self.primary_surface, self.camera.offset)
        self.player.render(self.primary_surface, self.camera.offset)
