from collections import defaultdict

import pygame
from pygame.surface import Surface
from tilemap_parser import (
    CollisionRunner,
    ICollidableSprite,
    PhysicsWorld,
    TileLayerRenderer,
    TilemapData,
    TilesetCollision,
    get_shape_aabb,
)


class IGroundCheckSprite(ICollidableSprite):
    flipped: bool


class WorldLoader:
    def __init__(
        self, map_data: TilemapData, tileset_collision: TilesetCollision, exclude_layers: set[str] | None = None
    ) -> None:
        self.physics_world = PhysicsWorld.from_map(
            map_data, tileset_collision, use_gids=True, exclude_layers=exclude_layers
        )

        self._exclude_layers(map_data, exclude_layers)
        self.collision_runner = CollisionRunner.from_world(self.physics_world, strict=True)
        self.tile_layer_renderer = TileLayerRenderer(map_data)

    def _exclude_layers(self, map_data: TilemapData, layer_ids: set[str] | None = None):
        if layer_ids is None:
            return
        for layer in map_data.get_layers(layer_type="tile"):
            if layer.name in layer_ids:
                layer.visible = False

    def is_ground_ahead(self, sprite: IGroundCheckSprite):
        """
        A common protocal has to be followed, by default character should face right
        or at least Flipped status when off should hint something is facing right.
        Note: This api doesnt account for ceiling
        """
        left, _, right, bottom = get_shape_aabb(sprite.x, sprite.y, sprite.collision_shape)
        probe_x, probe_y = left - 1 if sprite.flipped else right + 1, bottom + 1
        tile_x, tile_y = self.collision_runner.get_tile_at(probe_x, probe_y)
        tile_id = self.physics_world.tile_map.get((tile_x, tile_y))
        return tile_id is not None and self.physics_world.has_collision_gid(tile_id)

    @staticmethod
    def _transform(surf: pygame.Surface, x: float, y: float, render_scale: float = 1.0):
        sx = x * render_scale
        sy = y * render_scale
        surf = pygame.transform.scale_by(surf, render_scale)
        return (surf, sx, sy)

    @staticmethod
    def load_objects(
        tilemap_data: TilemapData,
        name_filter: set[str],
        classifier: set[str],
    ):
        """first return type is static object and second argument is dynamic object for user customization"""
        static_objects: list[tuple[Surface, float, float]] = []
        classification: dict[str, list[tuple[Surface, float, float]]] = defaultdict(list)

        for layer in tilemap_data.parsed.layers:
            exclude = (
                layer.layer_type != "object"
                or layer.name in name_filter
                or layer.properties.get("exclude")
                or not layer.visible
            )
            if exclude:
                continue

            objects = tilemap_data.get_object_surfaces(layer.name)
            for surf, x, y, oid in objects:
                properties = layer.objects[oid].properties
                if properties is None:
                    continue
                obj_name = properties.get("name")
                obj_type = properties.get("type")
                if properties.get("exclude") or obj_name in name_filter:
                    continue
                obj = WorldLoader._transform(surf, x, y, tilemap_data.render_scale)
                if obj_type in classifier:
                    classification[obj_type].append(obj)
                elif layer.name in classifier:
                    classification[layer.name].append(obj)
                else:
                    static_objects.append(obj)
        return static_objects, dict(classification)
