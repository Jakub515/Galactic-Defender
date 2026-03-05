import pygame
import math
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from space_ship import SpaceShip
    from jednostki.enemy_ship.enemy_manager import EnemyManager

# Globalny słownik na podręczną pamięć obróconych obrazków
ROTATION_CACHE: dict[int, dict[float, pygame.Surface]] = {}

def get_rotated_asteroid(original_image: pygame.Surface, angle: float) -> pygame.Surface:
    angle_idx = float(round(angle) % 360)
    img_id = id(original_image)
    if img_id not in ROTATION_CACHE:
        ROTATION_CACHE[img_id] = {}
    if angle_idx not in ROTATION_CACHE[img_id]:
        rotated = pygame.transform.rotate(original_image, angle_idx).convert_alpha()
        ROTATION_CACHE[img_id][angle_idx] = rotated
    return ROTATION_CACHE[img_id][angle_idx]
import pygame
import math
import random
from typing import TYPE_CHECKING, Any

# ... (funkcje rotacji i cache pozostają bez zmian) ...

class Asteroid:
    def __init__(self, planet_cat: list, space_cat: list, else_cat: list, meteor_images: list, 
                 center_pos: pygame.math.Vector2, spawn_radius: int, fixed_angle: float, world_radius: float):
        
        rand_val = random.random()
        
        if rand_val < 0.7:
            # 70% szans na Mały Meteor
            self.original_image = random.choice(meteor_images)
        elif rand_val < 0.9:
            # 20% szans na Planetę (łączymy planet_cat i else_cat)
            pool = planet_cat + else_cat
            self.original_image = random.choice(pool) if pool else random.choice(meteor_images)
        else:
            # 10% szans na Giga Asteroidę (space)
            self.original_image = random.choice(space_cat) if space_cat else random.choice(meteor_images)
        
        # Reszta inicjalizacji
       
        self.radius = self.original_image.get_width() / 2
        self.mass = self.radius * 0.1
        # ... (geometria rozstawienia i zabezpieczenie granic bez zmian) ...
        jitter_angle = random.uniform(-0.12, 0.12) 
        angle = fixed_angle + jitter_angle
        max_allowed_dist = world_radius - self.radius
        distance = random.gauss(mu=spawn_radius, sigma=spawn_radius * 0.03)
        distance = min(distance, max_allowed_dist)
        
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
        self.rect = pygame.Rect(0, 0, int(self.radius * 2), int(self.radius * 2))
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        
    def update(self, dt: float, player: "SpaceShip", enemies: list):
        self.pos += self.velocity
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.angle = (self.angle + self.rotation_speed) % 360
        
        if self.is_visible:
            self._apply_gravity(player, dt)
            for enemy in enemies:
                if not getattr(enemy, 'is_dead', False):
                    self._apply_gravity(enemy, dt)

    def _apply_gravity(self, target: Any, dt: float):
        target_pos = getattr(target, 'player_pos', getattr(target, 'pos', None))
        if target_pos is None: return
        rel_x = self.pos.x - target_pos.x
        rel_y = self.pos.y - target_pos.y
        dist_sq = rel_x**2 + rel_y**2
        if 100 < dist_sq < self.gravity_range_sq:
            distance = math.sqrt(dist_sq)
            force_magnitude = self.mass / (distance * 0.5) 
            gravity_vector = pygame.math.Vector2(rel_x, rel_y) / distance * force_magnitude * dt * 50
            target.velocity += gravity_vector

    def draw(self, window: pygame.Surface, cam_x: float, cam_y: float):
        draw_x = self.pos.x - cam_x
        draw_y = self.pos.y - cam_y
        rotated = get_rotated_asteroid(self.original_image, self.angle)
        rect = rotated.get_rect(center=(int(draw_x), int(draw_y)))
        window.blit(rotated, rect.topleft)
class AsteroidManager:
    def __init__(self, ship_frames: dict, zones_list: list, world_radius: float):
        # Trzy kategorie planet/dużych obiektów
        self.cat_planet: list[pygame.Surface] = []
        self.cat_space: list[pygame.Surface] = []
        self.cat_else: list[pygame.Surface] = []
        self.meteor_images: list[pygame.Surface] = []
        
        self.asteroids: list[Asteroid] = []
        self.world_radius = world_radius
        
        for path, image in ship_frames.items():
            if path.startswith("images/Meteors/"):
                img = image.convert_alpha()
                path_lower = path.lower()
                
                # Podział na kategorie zgodnie z nazwą pliku
                if "planet" in path_lower:
                    scale = 150 / max(img.get_width(), img.get_height())
                    new_img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                    self.cat_planet.append(new_img)
                elif "space" in path_lower:
                    scale = 250 / max(img.get_width(), img.get_height())
                    new_img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                    self.cat_space.append(new_img)
                elif any(word in path_lower for word in ["else", "other"]): # Obsługa "else" w nazwie
                    scale = 200 / max(img.get_width(), img.get_height())
                    new_img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                    self.cat_else.append(new_img)
                else:
                    scale = 60 / max(img.get_width(), img.get_height())
                    new_img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                    self.meteor_images.append(new_img)

        self._precompute_all_rotations()
        self.reinit_asteroid_data(zones_list, self.world_radius)

    def _precompute_all_rotations(self):
        all_imgs = self.cat_planet + self.cat_space + self.cat_else + self.meteor_images
        for img in list(set(all_imgs)):
            for angle in range(360):
                get_rotated_asteroid(img, float(angle))

    def reinit_asteroid_data(self, zones_list: list, world_radius: float):
        self.asteroids.clear()
        self.world_radius = world_radius

        for zone in zones_list:
            count = zone["count"]
            center_pos = zone["pos"]
            spawn_radius = zone["radius"]
            angle_step = (2 * math.pi) / count
            
            for i in range(count):
                target_angle = i * angle_step
                self.asteroids.append(Asteroid(
                    self.cat_planet, self.cat_space, self.cat_else, self.meteor_images, 
                    center_pos, spawn_radius, target_angle, self.world_radius
                ))
        
        for _ in range(15):
            self.resolve_overlaps(only_visible=False)

    def resolve_overlaps(self, only_visible: bool = True):
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
                asteroid.draw(window, cam_x, cam_y)
            else:
                asteroid.is_visible = False