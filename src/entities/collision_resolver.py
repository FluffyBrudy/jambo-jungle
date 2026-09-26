from tilemap_parser import CollisionHit, ICollidable

from src.entities.base import Character
from src.entities.enemies import Grunt
from src.entities.player import Player
from src.projectile.bullet import WeaponBullet


def resolve_collision(collision_hit: CollisionHit, /):
    if not resolve_bullet_collision(collision_hit):
        if not resolve_entity_entity_collision(collision_hit):
            pass


def resolve_bullet_collision(collision_hit: CollisionHit, /):
    a = collision_hit.object_a
    b = collision_hit.object_b

    if isinstance(a, WeaponBullet):
        bullet, target = a, b
    elif isinstance(b, WeaponBullet):
        bullet, target = b, a
    else:
        return False

    if isinstance(target, (Player, Grunt)) and target.can_hit():
        bullet.is_dead = True
        target.trigger_hit_effect()
        return True
    return False


def resolve_entity_entity_collision(collision_hit: CollisionHit, /):
    a = collision_hit.object_a
    b = collision_hit.object_b
    if not (isinstance(a, Character) or isinstance(b, Character)):
        return False
    if isinstance(a, Player):
        player, _ = a, b
    if isinstance(b, Player):
        player, _ = b, a
    else:
        return False

    player.trigger_hit_effect()
    return True
