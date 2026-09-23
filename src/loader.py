from pygame import Surface
from tilemap_parser import TilemapData


class SharedData:
    __instance: "SharedData" = None  # pyright: ignore

    def preload(self, mapdata: TilemapData):
        pass

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance


class LevelData:
    __instance: "LevelData" = None  # pyright: ignore
    __initialized = False

    def __init__(self) -> None:
        if self.__initialized:
            return
        self.objects_before_tiles: list[tuple[Surface, float, float]] = []
        self.objects_after_tiles: list[tuple[Surface, float, float]] = []
        self.__initialized = True

    def preload(self, mapdata: TilemapData):
        self.objects_before_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects_bg", scaled=True)
        ]
        self.objects_after_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects", scaled=True)
        ]

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        return cls.__instance
