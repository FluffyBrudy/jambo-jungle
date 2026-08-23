from pathlib import Path
from typing import cast

from tilemap_parser import (
    CollisionRunner,
    ICollidableSprite,
    PhysicsWorld,
    TileLayerRenderer,
    TilemapData,
    TilesetCollision,
    get_shape_aabb,
    load_map,
    load_tileset_collision,
)

from src.settings import ROOT_PATH


class IGroundCheckSprite(ICollidableSprite):
    flipped: bool


class WorldLoader:
    def __init__(self, map_suffix: str) -> None:
        map_path = ROOT_PATH / "data" / "maps" / (map_suffix + ".json")
        tileset_collision_path = ROOT_PATH / "data" / "collision" / "tileset.collision.json"

        assert map_path.exists()
        assert tileset_collision_path.exists()

        map_data = load_map(map_path)
        tileset_collision = cast(TilesetCollision, load_tileset_collision(tileset_collision_path))

        self.physics_world = PhysicsWorld.from_map(map_data, tileset_collision, use_gids=True)
        self.collision_runner = CollisionRunner.from_world(self.physics_world, strict=True)
        self.tile_layer_renderer = TileLayerRenderer(map_data)

    def is_ground_ahead(self, sprite: IGroundCheckSprite):
        """
        A common protocal has to be followed, by default character should face right
        or at least Flipped status when off should hint something is facing right.
        Note: This api doesnt account for ceiling
        """
        left, _, bottom, right = get_shape_aabb(sprite.x, sprite.y, sprite.collision_shape)
        probe_x, probe_y = left - 1 if sprite.flipped else right + 1, bottom + 1
        tile_x, tile_y = self.collision_runner.get_tile_at(probe_x, probe_y)
        tile_id = self.physics_world.tile_map.get((tile_x, tile_y))
        return tile_id is not None and self.physics_world.tileset_collision.has_collision(tile_id)  # pyright: ignore

    def load_static_objects(self, tilemap_data: TilemapData):
        for layer in tilemap_data.parsed.layers:
            if layer.layer_type != "object" or not layer.visible:
                continue
            for obj in layer.objects.values():
