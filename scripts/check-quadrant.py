import sys
from math import atan2, ceil, degrees, floor, radians

import pygame


class Game:
    """
    Just attempt quantizing for rotating turrent insted of full 360
    """

    WIDTH = 1280
    HEIGHT = 720
    FPS = 60
    TITLE = "Pygame"
    BG_COLOR = (30, 30, 30)

    def __init__(self) -> None:
        self.running = True
        self._init()

        self.simple_rect = pygame.Rect(0, 0, 80, 80)
        self.simple_rect.center = self.WIDTH // 2, self.HEIGHT // 2
        self.font = pygame.Font(None, 20)
        self.font_sm = pygame.Font(None, 15)

    def _init(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(self.TITLE)
        self.clock = pygame.time.Clock()

    def handle_event(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self, dt: float) -> None:
        pass

    def render(self) -> None:
        self.screen.fill(self.BG_COLOR)
        pygame.draw.rect(self.screen, "green", self.simple_rect)
        simple_lable_pos = self.font_sm.render(f"{self.simple_rect.center}", True, (0, 0, 0))
        self.screen.blit(simple_lable_pos, self.simple_rect.midleft)
        mouse_pos = pygame.mouse.get_pos()
        pos_label = self.font.render(f"{mouse_pos}", True, (255, 255, 255))
        diff_x, diff_y = pygame.Vector2(mouse_pos) - self.simple_rect.center
        diff_label = self.font.render(f"{(diff_x, diff_y)}", True, "white")
        angle_label = degrees(atan2(diff_y, diff_x))
        l_angle_label = (angle_label // 45) * 45
        r_angle_label = ceil(angle_label / 45) * 45
        dp = (l_angle_label + r_angle_label) / 2
        v = l_angle_label
        if angle_label >= dp:
            v = r_angle_label
        angle_surf = self.font.render(f"{(l_angle_label, angle_label, r_angle_label)}, decision={v}", True, "white")
        x, y, w, h = self.screen.blit(pos_label, (mouse_pos[0] + 20, mouse_pos[1] + 20))
        x, y, w, h = self.screen.blit(diff_label, (mouse_pos[0] + 20, y + h + 20))
        self.screen.blit(angle_surf, (mouse_pos[0] + 20, y + h + 20))
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
