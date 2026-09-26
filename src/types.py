from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from pygame import Surface
from tilemap_parser import ICollidable


class WorldObject(ICollidable, Protocol):
    def update(self, dt: float): ...
    def render(self, surface: Surface, offset: tuple[float, float]): ...


@runtime_checkable
class Killable(ICollidable, Protocol):
    def can_kill(self) -> bool: ...


@runtime_checkable
class Hitable(ICollidable, Protocol):
    def can_hit(self) -> bool: ...


TSpawnBulletCb = Callable[[float, float, str, int, tuple[float, float] | None], Any]
