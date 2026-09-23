from typing import TYPE_CHECKING

import pygame
from tilemap_parser import TileLayerRenderer, load_map

from src.loader import LevelData, SharedData
from src.settings import PROJECT_PATH

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

        self.tile_renderer = TileLayerRenderer(mapdata)
        self.objects_before_tiles = LevelData().objects_before_tiles
        self.objects_after_tiles = LevelData().objects_after_tiles

    def update(self, dt: float):
        pass

    def render(self):
        for surf, x, y in self.objects_before_tiles:
            self.screen.blit(surf, (x - 0, y - 0))
        self.tile_renderer.render(self.screen, (0, 0))
        for surf, x, y in self.objects_after_tiles:
            self.screen.blit(surf, (x - 0, y - 0))
