from pygame import Vector2
from tilemap_parser import CircleShape, ICollidable


class Projectile(ICollidable):
    def __init__(self, x: float, y: float, radius: float, velocity: tuple[float, float]) -> None:
        self.x = x
        self.y = y
        self.velocity = Vector2(velocity)
        self.collision_shape = CircleShape(radius)

    def update(self, dt: float) -> bool | None:
        self.x += self.velocity.x * dt
        self.y += self.velocity.y * dt
