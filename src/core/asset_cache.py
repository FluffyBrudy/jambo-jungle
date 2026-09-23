from __future__ import annotations

from pathlib import Path

from tilemap_parser import (
    CharacterCollision,
    SpriteAnimationSet,
    get_cached_character_collision,
)

_anim_cache: dict[tuple[str, float], SpriteAnimationSet] = {}


def get_animation_set(animation_path: Path | str, render_scale: float = 1.0) -> SpriteAnimationSet:
    """Return shared ``SpriteAnimationSet`` for ``(path, render_scale)``.

    The registry is global to :mod:`src.core.asset_cache` so all entity
    types share the same underlying ``surface`` / ``library`` when they
    request the same file with the same ``render_scale``. ``SpriteAnimationSet``
    is immutable after ``load()`` (see ``tilemap_parser/runtime/animation_player.py:28``),
    so sharing is safe. ``AnimationPlayer`` instances remain per-entity
    (``animation_player.py:143``).
    """
    key = (str(Path(animation_path).resolve()), float(render_scale))
    if key not in _anim_cache:
        _anim_cache[key] = SpriteAnimationSet.load(animation_path, render_scale=render_scale)
    return _anim_cache[key]


def get_character_collision(
    collision_path: Path | str, render_scale: float = 1.0
) -> CharacterCollision | None:
    """Thin wrapper around ``tilemap_parser.get_cached_character_collision``.

    Exposed here so callers have a single shared asset module.
    """
    return get_cached_character_collision(collision_path, render_scale=render_scale)


def clear_animation_cache() -> None:
    _anim_cache.clear()


def clear_all_caches() -> None:
    from tilemap_parser import clear_collision_cache

    clear_animation_cache()
    clear_collision_cache()
