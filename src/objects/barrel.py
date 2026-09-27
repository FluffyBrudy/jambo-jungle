from pygame.surface import Surface
from tilemap_parser import AnimationPlayer, RectangleShape, get_shape_aabb

from src.loader import SharedData

EXPLOSION_HIT_THRESHOLD = 5


class BarrelRed:
    def __init__(self, x: float, y: float) -> None:
        collision_data = SharedData().character_collisions["barrel_red"]
        explosion_animation_set = SharedData().state_animations["explosion"]
        self.surface = SharedData().images["barrel_red"]
        self.explosion_animation = AnimationPlayer(explosion_animation_set, "red")
        self.x = x
        self.y = y
        self.collision_shape = collision_data.shape
        self.collision_mask = collision_data.collision_mask
        self.collision_layer = collision_data.collision_layer

        self.hit_count = 0
        self.exploded = False

    def update(self, dt: float):
        if self.exploded:
            self.explosion_animation.update(dt * 1000)

    def can_hit(self):
        return not self.exploded

    def can_kill(self):
        return self.exploded and self.explosion_animation.finished

    def trigger_hit_effect(self, full: bool = False):
        self.hit_count += 1 if not full else (EXPLOSION_HIT_THRESHOLD + 1)
        if self.hit_count > EXPLOSION_HIT_THRESHOLD and not self.exploded:
            self.exploded = True
            self.explosion_animation.reset()
            l, t, r, b = get_shape_aabb(self.x, self.y, self.collision_shape)
            w, h = (r - l), (b - t)
            self.collision_shape = RectangleShape(w * 3, h * 2)
            SharedData().soundmanager.play("explosion_ground", "sfx")

    def render(self, surface: Surface, offset: tuple[float, float]):
        if not self.exploded:
            surface.blit(self.surface, (self.x - offset[0], self.y - offset[1]))
        else:
            frame = self.explosion_animation.get_current_image()
            if frame is None:
                return
            surface.blit(frame, (self.x - offset[0], self.y - offset[1]))
