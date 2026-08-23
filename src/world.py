from typing import TYPE_CHECKING

from src.core.loader import WorldLoader

if TYPE_CHECKING:
    from game import Game


class World:
    def __init__(self, game: "Game") -> None:
        self.game = game
        self.primary_surface = self.game.screen

        self.world = WorldLoader("0")

    def render(self):
        self.world.tile_layer_renderer.render(self.primary_surface)
