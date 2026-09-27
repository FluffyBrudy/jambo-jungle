import pygame
from pygame.surface import Surface
from pygkit.transitions import Flash, IrisOut, Shake


class IntroTransition:
    IRIS_DURATION = 1.2
    FLASH_DURATION = 0.25
    SHAKE_DURATION = 0.35
    SHAKE_INTENSITY = 5.0

    def __init__(self) -> None:
        self._iris = IrisOut()
        self._iris.start(self.IRIS_DURATION)
        self._flash = Flash()
        self._shake = Shake(intensity=self.SHAKE_INTENSITY)
        self._pop_started = False
        self.done = False

    def skip(self) -> None:
        self.done = True

    def reset(self) -> None:
        self._iris.start(self.IRIS_DURATION)
        self._flash.reset()
        self._shake.reset()
        self._pop_started = False
        self.done = False

    def update(self, dt: float) -> None:
        if self.done:
            return
        self._iris.update(dt)
        if self._iris.done and not self._pop_started:
            self._flash.start(self.FLASH_DURATION)
            self._shake.start(self.SHAKE_DURATION)
            self._pop_started = True
        if self._pop_started:
            self._flash.update(dt)
            self._shake.update(dt)
            if self._flash.done and self._shake.done:
                self.done = True

    def render(self, screen: Surface) -> None:
        if self.done:
            return
        self._iris.render(screen)
        if not self._pop_started:
            return
        self._flash.render(screen)
        if not self._shake.done:
            snap = screen.copy()
            screen.fill((0, 0, 0))
            self._shake.render(screen, source=snap)

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.done and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.skip()
