from tilemap_parser import ICollidable

from .enemies import Enemy, Grunt
from .player import Player


def resolve_player_vs_shooter(player: Player, obj: ICollidable):
    if isinstance(obj, Grunt):
