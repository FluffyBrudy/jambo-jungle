from typing import Protocol, runtime_checkable

from pygame import Surface
from tilemap_parser import ICollidable


class WorldObject(ICollidable, Protocol):
    def update(self, dt: float): ...
    def render(self, surface: Surface, offset: tuple[float, float]): ...


@runtime_checkable
class Killable(Protocol):
    def can_kill(self) -> bool: ...
