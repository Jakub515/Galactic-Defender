import pygame
import random

class Debris:
    def __init__(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2, color: tuple | list):
        self.pos = pygame.math.Vector2(pos)
        self.velocity = velocity + pygame.math.Vector2(random.uniform(-4, 4), random.uniform(-4, 4))
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-15, 15)
        self.life = 1.0  
        self.decay = random.uniform(0.01, 0.02) 
        self.size = random.randint(3, 7)
        self.color = color

    def update(self):
        self.pos += self.velocity
        self.angle += self.rot_speed
        self.life -= self.decay
        self.velocity *= 0.97  

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        if self.life <= 0: return
        alpha = int(self.life * 255)
        s = self.size
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        surf.fill((*self.color, alpha))
        window.blit(surf, (self.pos.x - camera_x - s//2, self.pos.y - camera_y - s//2))
