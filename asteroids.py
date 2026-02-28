import pygame
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_ship import SpaceShip
    from enemy_ship import EnemyManager

# Globalny słownik na podręczną pamięć obróconych obrazków
ROTATION_CACHE = {}

def get_rotated_asteroid(original_image: pygame.Surface, angle: float):
    """Pobiera gotowy obrazek z cache. Precyzja 1 stopień (wystarczy dla RAM)."""
    angle = round(angle) % 360
    img_id = id(original_image)
    
    try:
        return ROTATION_CACHE[img_id][angle]
    except KeyError:
        if img_id not in ROTATION_CACHE:
            ROTATION_CACHE[img_id] = {}
        rotated = pygame.transform.rotate(original_image, angle).convert_alpha()
        ROTATION_CACHE[img_id][angle] = rotated
        return rotated

class Asteroid:
    def __init__(self, planet_images: list, meteor_images: list, center_pos: pygame.math.Vector2, spawn_radius: int, fixed_angle: float):
        if planet_images and random.random() < 0.1:
            self.original_image = random.choice(planet_images)
        else:
            self.original_image = random.choice(meteor_images)
        
        self.radius = self.original_image.get_width() / 2
        self.mass = self.radius * 0.1
        
        # Geometria koła
        jitter_angle = random.uniform(-0.12, 0.12) 
        angle = fixed_angle + jitter_angle
        distance = random.gauss(mu=spawn_radius, sigma=spawn_radius * 0.03)
        
        self.pos = pygame.math.Vector2(
            center_pos.x + math.cos(angle) * distance,
            center_pos.y + math.sin(angle) * distance
        )
        
        self.velocity = pygame.math.Vector2(random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.uniform(0.2, 0.6) * random.choice([-1, 1])
        
        self.gravity_range = self.radius * 8
        self.gravity_range_sq = self.gravity_range ** 2
        self.is_visible = False

        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (int(self.pos.x), int(self.pos.y))

    def update(self, dt: float, player: "SpaceShip", enemies: list):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.angle = (self.angle + self.rotation_speed) % 360
        if self.is_visible:
            self._apply_gravity(player, dt)
            for enemy in enemies:
                if not enemy.is_dead:
                    self._apply_gravity(enemy, dt)

    def _apply_gravity(self, target, dt: float):
        target_pos = target.player_pos if hasattr(target, 'player_pos') else target.pos
        rel_x = self.pos.x - target_pos.x
        rel_y = self.pos.y - target_pos.y
        dist_sq = rel_x**2 + rel_y**2
        if 100 < dist_sq < self.gravity_range_sq:
            distance = math.sqrt(dist_sq)
            force_magnitude = self.mass / (distance * 0.5) 
            gravity_vector = pygame.math.Vector2(rel_x, rel_y) / distance * force_magnitude * dt * 50
            target.velocity += gravity_vector

    def draw(self, window: pygame.Surface, cam_x: float, cam_y: float, screen_w: int, screen_h: int):
        # Tutaj rysujemy używając już obliczonego wcześniej self.is_visible
        draw_x = self.pos.x - cam_x
        draw_y = self.pos.y - cam_y
        
        rotated = get_rotated_asteroid(self.original_image, self.angle)
        # Pobieramy rect tylko do blitowania (lokalny dla ekranu)
        rect = rotated.get_rect(center=(int(draw_x), int(draw_y)))
        window.blit(rotated, rect.topleft)

class AsteroidManager:
    def __init__(self, ship_frames: dict, zones_list: list):
        self.planet_images = []
        self.meteor_images = []
        
        # 1. Agresywne filtrowanie i skalowanie (KLUCZ DO RAM)
        for path, image in ship_frames.items():
            if path.startswith("images/Meteors/"):
                img = image.convert_alpha()
                if "planet" in path.lower():
                    # Planety skalujemy do max 150px
                    scale = 150 / max(img.get_width(), img.get_height())
                    new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
                    img = pygame.transform.smoothscale(img, new_size)
                    self.planet_images.append(img)
                else:
                    # Meteoryty skalujemy do max 60px
                    scale = 60 / max(img.get_width(), img.get_height())
                    new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
                    img = pygame.transform.smoothscale(img, new_size)
                    self.meteor_images.append(img)

        # 2. Generowanie cache (z precyzją 1 stopień)
        self._precompute_all_rotations()

        # 3. Tworzenie obiektów
        self.asteroids = []
        for zone in zones_list:
            count = zone["count"]
            angle_step = (2 * math.pi) / count
            for i in range(count):
                target_angle = i * angle_step
                self.asteroids.append(Asteroid(
                    self.planet_images, self.meteor_images, 
                    zone["pos"], zone["radius"], target_angle
                ))
        
        for _ in range(10): # Mniej iteracji dla szybkości startu
            self.resolve_overlaps(only_visible=False)

    def _precompute_all_rotations(self):
        """Zoptymalizowane generowanie cache'u (360 klatek na obrazek)."""
        all_unique_images = list(set(self.planet_images + self.meteor_images))
        
        for img in all_unique_images:
            img_id = id(img)
            ROTATION_CACHE[img_id] = {}
            for angle in range(360):
                # Rotacja i convert_alpha() dla optymalizacji RAM
                ROTATION_CACHE[img_id][float(angle)] = pygame.transform.rotate(img, angle).convert_alpha()

    def resolve_overlaps(self, only_visible=True):
        active = [a for a in self.asteroids if a.is_visible] if only_visible else self.asteroids
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                ast1, ast2 = active[i], active[j]
                diff = ast1.pos - ast2.pos
                dist_sq = diff.length_squared()
                min_dist = (ast1.radius + ast2.radius) * 1.1
                if 0 < dist_sq < min_dist**2:
                    dist = math.sqrt(dist_sq)
                    push = (diff / dist) * ((min_dist - dist) * 0.15)
                    ast1.pos += push
                    ast2.pos -= push

    def update(self, dt: float, player: "SpaceShip", enemy_manager: "EnemyManager"):
        self.resolve_overlaps(only_visible=True)
        enemies = enemy_manager.enemies
        for asteroid in self.asteroids:
            asteroid.update(dt, player, enemies)

    def draw(self, window: pygame.Surface, cam_x: float, cam_y: float, screen_w: int, screen_h: int):
        view_rect = pygame.Rect(cam_x - 150, cam_y - 150, screen_w + 300, screen_h + 300)
        
        for asteroid in self.asteroids:
            if view_rect.colliderect(asteroid.rect):
                asteroid.is_visible = True
                asteroid.draw(window, cam_x, cam_y, screen_w, screen_h)
            else:
                asteroid.is_visible = False