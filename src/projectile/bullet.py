from typing import Literal, override

from pygkit import AnimationPlayer, AnimationSheet

from src.projectile.base import Projectile
from src.settings import ROOT_PATH

TBulletType = Literal["player_bullet", "enemy_bullet"]
TFireEffectType = Literal["player_fire_effect"]


class SimpleAnimatedBullet(Projectile):
    objects: set["SimpleAnimatedBullet"] = set()
    fps = 10

    @classmethod
    def init(cls):
        cls.player_sheet = AnimationSheet.load(
            ROOT_PATH / "assets" / "images" / "SpriteSheets" / "player" / "weapon_bullet.png",
            rows=1,
            cols=8,
        )

        cls.enemy_sheet = AnimationSheet.load(
            ROOT_PATH / "assets" / "images" / "SpriteSheets" / "enemy" / "enemy_weapon_bullet.png",
            rows=1,
            cols=8,
        )

    @classmethod
    def add(cls, bullet: "SimpleAnimatedBullet"):
        cls.objects.add(bullet)

    def __hash__(self) -> int:
        return id(self)

    def __init__(self, x: float, y: float, velocity: tuple[float, float], bullet_type: TBulletType):
        super().__init__(x, y, 0, velocity)

        self.animation_player = AnimationPlayer(loop=False, fps=self.fps)
        sheet = self.player_sheet if bullet_type == "player_bullet" else self.enemy_sheet
        self.animation_player.play(bullet_type, sheet=sheet)
        self.kill = False

    @override
    def update(self, dt: float) -> bool:
        super().update(dt)
        self.animation_player.update(dt * 1000 * (SimpleAnimatedBullet.fps / 60))
        return not self.animation_player.finished or self.kill


class BulletSpark:
    objects: set["BulletSpark"] = set()
    fps = 60

    @classmethod
    def init(cls):
        cls.player_sheet = AnimationSheet.load(
            ROOT_PATH / "assets" / "images" / "SpriteSheets" / "fx" / "bullet_ricochet_spark.png",
            rows=1,
            cols=16,
        )

    def __init__(self) -> None:
        self.animation_player = AnimationPlayer(fps=BulletSpark.fps)
        self.animation_player.play("shoot", sheet=self.player_sheet)

    def update(self, dt: float) -> bool:
        self.animation_player.update(dt * 1000 * (SimpleAnimatedBullet.fps / 60))
        return not self.animation_player.finished
