from typing import cast

from pygame import Surface
from tilemap_parser import (
    CharacterCollision,
    ParsedLayer,
    SpriteAnimationSet,
    TilemapData,
    TilesetCollision,
    get_cached_character_collision,
    get_cached_tileset_collision,
)

from src.settings import PROJECT_PATH


class SharedData:
    __instance: "SharedData" = None  # pyright: ignore
    __initialized = False

    def __init__(self) -> None:
        if self.__initialized:
            return
        self.__initialized = True

        self.state_animations = {}
        self.character_collisions = {}
        self.tileset_collision = {}

    def preload(self, mapdata: TilemapData):
        self.state_animations = {
            "player": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/player.anim.json", render_scale=mapdata.render_scale
            ),
        }
        self.character_collisions = {
            "player": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/player.collision.json", render_scale=mapdata.render_scale
                ),
            ),
        }
        self.tileset_collision = {
            "default": cast(
                TilesetCollision, get_cached_tileset_collision(PROJECT_PATH / "data/collision/tileset.collision.json")
            ),
        }

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance


class LevelData:
    __instance: "LevelData" = None  # pyright: ignore
    __initialized = False

    def __init__(self) -> None:
        if self.__initialized:
            return
        self.__initialized = True

        self.objects_before_tiles: list[tuple[Surface, float, float]] = []
        self.objects_after_tiles: list[tuple[Surface, float, float]] = []
        self.player_pos = (0, 0)

    def preload(self, mapdata: TilemapData):
        layer = cast(ParsedLayer, mapdata.get_layer("entities"))

        entites = mapdata.get_object_surfaces("entities", scaled=True)
        for _, x, y, oid in entites:
            props = mapdata.parsed.tilesets[layer.objects[oid].ttype].properties
            if props and props.get("name") == "player":
                self.player_pos = (x, y)

        self.objects_before_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects_bg", scaled=True)
        ]
        self.objects_after_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects", scaled=True)
        ]

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
