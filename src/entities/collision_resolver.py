from tilemap_parser import CollisionHit, ICollidable

from src.entities.base import Character
from src.entities.enemies import Grunt, GruntSpawnPortal
from src.entities.player import Player
from src.objects.barrel import BarrelRed
from src.projectile.bullet import WeaponBullet


def resolve_collision(collision_hit: CollisionHit, /):
    if not resolve_bullet_collision(collision_hit):
        if not resolve_entity_entity_collision(collision_hit):
            if not resolve_entity_object_collision(collision_hit):
                if not resolve_object_object_collision(collision_hit):
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

    if isinstance(target, (Player, Grunt, GruntSpawnPortal, BarrelRed)) and target.can_hit():
        bullet.is_dead = True
        target.trigger_hit_effect()
        return True
    return False


def resolve_entity_entity_collision(collision_hit: CollisionHit, /):
    a = collision_hit.object_a
    b = collision_hit.object_b
    if not (isinstance(a, Character) and isinstance(b, Character)):
        return False
    if isinstance(a, Player):
        player, _ = a, b
    elif isinstance(b, Player):
        player, _ = b, a
    else:
        return False
    if player.can_hit():
        player.trigger_hit_effect()
        return True
    return False


def resolve_entity_object_collision(collision_hit: CollisionHit, /):
    a = collision_hit.object_a
    b = collision_hit.object_b

    if isinstance(a, (Player, Grunt)):
        entity, obj = a, b
    elif isinstance(b, (Player, Grunt)):
        entity, obj = b, a
    else:
        return False

    if isinstance(obj, BarrelRed) and obj.exploded and entity.can_hit():
        entity.trigger_hit_effect(True)
        return True
    return False


def resolve_object_object_collision(collision_hit: CollisionHit):
    a = collision_hit.object_a
    b = collision_hit.object_b

    if isinstance(a, BarrelRed) and isinstance(b, BarrelRed):
        if (a.exploded and a.explosion_animation.frame_index > 2) or (
            b.exploded and b.explosion_animation.frame_index > 2
        ):
            a.trigger_hit_effect(True)
            b.trigger_hit_effect(True)
            return True
    if isinstance(a, GruntSpawnPortal) and isinstance(b, BarrelRed) and b.exploded:
        a.trigger_hit_effect(True)
        return True
    if isinstance(b, GruntSpawnPortal) and isinstance(a, BarrelRed) and a.exploded:
        b.trigger_hit_effect(True)
        return True
    return False
