from collections import defaultdict
from typing import cast

from pygame import Surface
from pygame.rect import Rect
from pygkit.audio import SoundManager
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
from src.utils.utils import load_image


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

        self.render_scale = 1.0

    def preload(self, mapdata: TilemapData):
        self.render_scale = mapdata.render_scale
        self.state_animations = {
            "player": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/player.anim.json", render_scale=mapdata.render_scale
            ),
            "grunt": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/grunt.anim.json", render_scale=mapdata.render_scale
            ),
            "turret": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/turret.anim.json", render_scale=mapdata.render_scale
            ),
            "weapon_bullets": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/weapn_bullets.anim.json", render_scale=mapdata.render_scale
            ),
            "explosion": SpriteAnimationSet.load(
                PROJECT_PATH / "data/animations/explosion.anim.json", render_scale=mapdata.render_scale
            ),
        }
        self.images = {
            "grunt_portal": load_image(
                PROJECT_PATH / "assets/images/SpriteSheets/enemy/grunt_portal.png", mapdata.render_scale
            ),
            "grunt_portal_broke": load_image(
                PROJECT_PATH / "assets/images/SpriteSheets/enemy/grunt_portal_broke.png", mapdata.render_scale
            ),
            "barrel_red": load_image(
                PROJECT_PATH / "assets/images/SpriteSheets/props/red_barrel.png", mapdata.render_scale
            ),
        }
        self.character_collisions = {
            "player": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/player.collision.json", render_scale=mapdata.render_scale
                ),
            ),
            "grunt": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/grunt.collision.json", render_scale=mapdata.render_scale
                ),
            ),
            "grunt_portal": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/grunt_portal.collision.json",
                    render_scale=mapdata.render_scale,
                ),
            ),
            "turret": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/turret.collision.json", render_scale=mapdata.render_scale
                ),
            ),
            "weapon_bullet": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/weapn_bullets.collision.json",
                    render_scale=mapdata.render_scale,
                ),
            ),
            "barrel_red": cast(
                CharacterCollision,
                get_cached_character_collision(
                    PROJECT_PATH / "data/character_collision/red_barrel.collision.json",
                    render_scale=mapdata.render_scale,
                ),
            ),
        }
        self.tileset_collision = {
            "default": cast(
                TilesetCollision, get_cached_tileset_collision(PROJECT_PATH / "data/collision/tileset.collision.json")
            ),
        }

        self.soundmanager = SoundManager()
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_main_theme.ogg", "main", "main", volume=0.5)
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_rifle_shot.ogg", "shoot", "sfx", volume=0.1)
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_hurt.ogg", "hurt", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_jump.ogg", "jump", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_landing.ogg", "land", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_step1.ogg", "step1", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_step2.ogg", "step2", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_explosion_ground.ogg", "explosion_ground", "sfx")
        self.soundmanager.add_sound(PROJECT_PATH / "assets/audio/snd_explosion_earth.ogg", "explosion_earth", "sfx")

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
        self.enemies: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self.player_pos = (0, 0)
        self.grunt_spawner_nodes: list[Rect] = []
        self.barrels: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self.level_completed_node = Rect(0, 0, 0, 0)

    def preload(self, mapdata: TilemapData):
        layer = cast(ParsedLayer, mapdata.get_layer("entities"))

        entites = mapdata.get_object_surfaces("entities", scaled=True)
        for _, x, y, oid in entites:
            props = mapdata.parsed.tilesets[layer.objects[oid].ttype].properties
            if props:
                if props.get("name") == "player":
                    self.player_pos = (x, y)
                elif props.get("name") == "grunt":
                    self.enemies["grunt"].append((x, y))
                elif props.get("name") == "turret":
                    self.enemies["turret"].append((x, y))
                elif props.get("name") == "red_barrel":
                    self.barrels["red"].append((x, y))

        self.objects_before_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects_bg", scaled=True)
        ]
        self.objects_after_tiles = [
            (surface, x, y) for surface, x, y, _ in mapdata.get_object_surfaces("objects", scaled=True)
        ]

        for node in mapdata.area_nodes:
            if node.name == "level_completed":
                self.level_completed_node = node.rect
            elif node.name == "spawn_area":
                self.grunt_spawner_nodes.append(node.rect)

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
