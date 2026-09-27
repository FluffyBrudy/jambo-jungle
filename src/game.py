import sys

import pygame

from src.transition import IntroTransition
from src.world import World


class Game:
    WIDTH = 1280
    HEIGHT = 720
    FPS = 60
    TITLE = "Pygame"
    BG_COLOR = (135, 200, 249)

    def __init__(self) -> None:
        self.running = True
        self._init()

    def _init(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()

        self.world = World(self)
        self.world.load_level("0")

        self.intro = IntroTransition()

    def handle_event(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            self.intro.handle_event(event)

    def update(self, dt: float) -> None:
        if not self.intro.done:
            self.intro.update(dt)
            return
        nxt = self.world.can_load_next()
        if nxt is not None:
            self.world.load_level(nxt)
            self.intro.reset()
            return
        self.world.update(dt)

    def render(self) -> None:
        self.screen.fill(self.BG_COLOR)
        self.world.render()
        self.intro.render(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.FPS) / 1000.0
            self.handle_event()

            self.update(dt)
            self.render()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
