import pygame
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicManager
    from shoot import Shoot
    from asteroids import AsteroidManager
    from space_ship import SpaceShip

class Debris:
    """Klasa reprezentująca pojedynczy odłamek zniszczonego statku."""
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
        s = self.size
        debris_surf = pygame.Surface((s, s), pygame.SRCALPHA)
        alpha = int(self.life * 255)
        pygame.draw.rect(debris_surf, (*self.color, alpha), (0, 0, s, s))
        rotated_debris = pygame.transform.rotate(debris_surf, self.angle)
        rect = rotated_debris.get_rect(center=(self.pos.x - camera_x, self.pos.y - camera_y))
        window.blit(rotated_debris, rect.topleft)

class Enemy:
    def __init__(self, ship_frames: dict, player_ref: "SpaceShip", music_obj: "MusicManager", shoot_obj: "Shoot", enemy_manager: "EnemyManager", spawn_pos: pygame.math.Vector2, asteroid_manager: "AsteroidManager"):
        self.music_obj = music_obj
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.shoot_obj = shoot_obj
        self.manager = enemy_manager
        self.asteroid_manager = asteroid_manager 

        self.is_dead = False
        self.debris_list = []
        
        enemy_types = [
            ("images/Enemies/enemyBlack1.png", 0.18, 1), # Lekko zwiększony thrust
            ("images/Enemies/enemyBlack2.png", 0.15, 1),
            ("images/Enemies/enemyBlack3.png", 0.12, 1)
        ]
        self.texture_path, self.thrust_power, self.hp = random.choice(enemy_types)
        self.image = pygame.transform.rotate(self.ship_frames[self.texture_path], -90)

        self.pos = pygame.math.Vector2(spawn_pos)
        
        self.velocity = pygame.math.Vector2(0, 0)
        self.angle = random.uniform(0, 360)
        self.angular_velocity = 0
        self.angular_acceleration = 0.8 # Zwiększona skrętność
        self.angular_friction = 0.85
        self.max_speed = 9.0 
        self.linear_friction = 0.995

        self.weapons = [
            [self.ship_frames["images/Lasers/laserRed01.png"], 40, 5, 0.6],
            [self.ship_frames["images/Lasers/laserRed02.png"], 50, 3, 0.5],
            [self.ship_frames["images/Lasers/laserRed03.png"], 60, 2, 0.4]
        ]
        self.current_weapon = random.randint(0, len(self.weapons) - 1)
        self.weapon_timers = [0.0 for _ in range(len(self.weapons))]
        
        self.is_thrusting = False
        self.avoidance_side = random.choice([-1, 1])

    def death(self):
        if not self.is_dead:
            self.is_dead = True
            self.music_obj.play("images/audio/sfx_exp_medium4.wav", 0.2)
            colors = [(80, 80, 80), (40, 40, 40), (255, 150, 0), (255, 50, 0)]
            for _ in range(random.randint(10, 15)):
                self.debris_list.append(Debris(self.pos, self.velocity, random.choice(colors)))

    def update(self, dt: float):
        if self.is_dead:
            for d in self.debris_list: d.update()
            self.debris_list = [d for d in self.debris_list if d.life > 0]
            return

        SAFE_MARGIN = 500  
        BASE_AVOIDANCE = 350 # Zmniejszony bazowy dystans uniku, by nie błądzili
        speed_bonus = self.velocity.length() * 15
        total_avoid_dist = BASE_AVOIDANCE + speed_bonus

        dist_from_center = self.pos.length()

        if dist_from_center > self.manager.world_radius:
            self.death()
            return

        for i in range(len(self.weapon_timers)):
            self.weapon_timers[i] += dt

        # 1. Kierunek bazowy
        dir_to_player = (self.player_ref.player_pos - self.pos)
        dist_to_player = dir_to_player.length() or 1
        
        if dist_from_center > (self.manager.world_radius - SAFE_MARGIN):
            dir_to_center = -self.pos 
            target_angle = -math.degrees(math.atan2(dir_to_center.y, dir_to_center.x))
            self.is_thrusting = True 
        else:
            target_angle = -math.degrees(math.atan2(dir_to_player.y, dir_to_player.x))
            self.is_thrusting = dist_to_player > 300

        # 2. LOGIKA OMIJANIA ASTEROID
        asteroid_influence = pygame.math.Vector2(0, 0)
        nearby_asteroids = 0

        for asteroid in self.asteroid_manager.asteroids:
            dist_to_ast_sq = self.pos.distance_squared_to(asteroid.pos)
            avoid_threshold = ((asteroid.radius + total_avoid_dist) ** 2) * 1.5
            
            if dist_to_ast_sq < avoid_threshold:
                dist = math.sqrt(dist_to_ast_sq)
                diff = self.pos - asteroid.pos
                if diff.length() > 0:
                    # Miękka siła odpychania
                    push_force = (1.0 - (dist / (asteroid.radius + total_avoid_dist)))
                    asteroid_influence += diff.normalize() * push_force
                    nearby_asteroids += 1

        if nearby_asteroids > 0:
            target_rad = math.radians(-target_angle)
            target_dir_vec = pygame.math.Vector2(math.cos(target_rad), math.sin(target_rad))
            
            # Mniejszy mnożnik (1.5 zamiast 3.0), aby boty nie wpadały w panikę
            final_dir = (target_dir_vec + asteroid_influence * 1.5).normalize()
            target_angle = -math.degrees(math.atan2(final_dir.y, final_dir.x))
            
            # Hamowanie tylko przy bardzo dużym ryzyku kolizji
            if asteroid_influence.length() > 1.2:
                self.velocity *= 0.985

        # 3. Separacja od innych wrogów
        for other in self.manager.enemies:
            if other is self or other.is_dead: continue
            if self.pos.distance_to(other.pos) < 150:
                target_angle += 30 * self.avoidance_side

        # 4. Fizyka obrotu
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        if angle_diff > 2: self.angular_velocity += self.angular_acceleration
        elif angle_diff < -2: self.angular_velocity -= self.angular_acceleration
        
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        # 5. Fizyka ruchu
        rad = math.radians(-self.angle)
        forward_dir = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        
        if self.is_thrusting:
            current_thrust = self.thrust_power
            # Zwiększamy ciąg, gdy bot musi manewrować (omijać), żeby nie stał w miejscu
            if nearby_asteroids > 0:
                current_thrust *= 1.4
            self.velocity += forward_dir * current_thrust

        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)

        self.velocity *= self.linear_friction
        self.pos += self.velocity

        # 6. Strzelanie
        if nearby_asteroids == 0 or asteroid_influence.length() < 0.5:
            if dist_from_center < (self.manager.world_radius - SAFE_MARGIN):
                if abs(angle_diff) < 25 and dist_to_player < 850:
                    self.shoot()

    def shoot(self):
        w = self.weapons[self.current_weapon]
        if self.weapon_timers[self.current_weapon] >= w[3]:
            self.weapon_timers[self.current_weapon] = 0.0
            rad = math.radians(-self.angle)
            direction = pygame.math.Vector2(math.cos(rad), math.sin(rad))
            self.shoot_obj.create_missle({
                "pos": self.pos.copy(),
                "vel": direction * w[1],
                "img": w[0],
                "damage": w[2],
                "dir": self.angle,
                "is_enemy_shot": True
            })
            self.music_obj.play("images/audio/sfx_laser2.wav", 0.3)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        if self.is_dead:
            for d in self.debris_list: d.draw(window, camera_x, camera_y)
            return

        if self.is_thrusting:
            try:
                engine_img = self.ship_frames["images/Effects/fire03.png"]
                fire_rot = pygame.transform.rotate(engine_img, self.angle)
                fire_offset = pygame.math.Vector2(-35, 0).rotate(-self.angle)
                window.blit(fire_rot, fire_rot.get_rect(center=(self.pos.x - camera_x + fire_offset.x, self.pos.y - camera_y + fire_offset.y)))
            except KeyError: pass

        rotated = pygame.transform.rotate(self.image, self.angle)
        rect = rotated.get_rect(center=(self.pos.x - camera_x, self.pos.y - camera_y))
        window.blit(rotated, rect.topleft)

class EnemyManager:
    def __init__(self, ship_frames: dict, player_ref: "SpaceShip", music_obj: "MusicManager", max_enemies: int, shoot_obj: "Shoot", world_radius: int, asteroid_manager: "AsteroidManager"):
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.music_obj = music_obj
        self.shoot_obj = shoot_obj
        self.max_enemies = max_enemies
        self.world_radius = world_radius
        self.asteroid_manager = asteroid_manager
        self.enemies = []

    def update(self, dt: float):
        living_enemies = [e for e in self.enemies if not e.is_dead]
        
        if len(living_enemies) < self.max_enemies and random.random() < 0.02:
            spawn_radius = 1200
            valid_pos = None
            
            for _ in range(10):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(spawn_radius * 0.7, spawn_radius)
                test_pos = pygame.math.Vector2(
                    self.player_ref.player_pos.x + math.cos(angle) * dist,
                    self.player_ref.player_pos.y + math.sin(angle) * dist
                )
                if test_pos.length() < (self.world_radius - 150):
                    valid_pos = test_pos
                    break
            
            if valid_pos:
                self.enemies.append(Enemy(self.ship_frames, self.player_ref, self.music_obj, self.shoot_obj, self, valid_pos, self.asteroid_manager))

        for enemy in self.enemies[:]:
            enemy.update(dt)
            if enemy.is_dead and len(enemy.debris_list) == 0:
                self.enemies.remove(enemy)

    def draw(self, window: pygame.Surface, camera_x:float, camera_y:float):
        for enemy in self.enemies:
            enemy.draw(window, camera_x, camera_y)