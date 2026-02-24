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
        # Odłamki dziedziczą pęd statku plus losowy rozrzut
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
    def __init__(self, ship_frames: dict, player_ref: "SpaceShip", music_obj: "MusicManager", 
                 shoot_obj: "Shoot", enemy_manager: "EnemyManager", spawn_pos: pygame.math.Vector2, 
                 asteroid_manager: "AsteroidManager", blue_fire_frames: list):
        # ... (zachowujemy istniejące inicjalizacje) ...
        self.music_obj = music_obj
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.shoot_obj = shoot_obj
        self.manager = enemy_manager
        self.asteroid_manager = asteroid_manager 

        self.is_dead = False
        self.debris_list = []
        
        enemy_configs = [
            ("images/Enemies/enemyBlack1.png", 1),
            ("images/Enemies/enemyBlack2.png", 1),
            ("images/Enemies/enemyBlack3.png", 1)
        ]
        self.texture_path, self.hp = random.choice(enemy_configs)
        self.image = pygame.transform.rotate(self.ship_frames[self.texture_path], -90)

        self.pos = pygame.math.Vector2(spawn_pos)
        self.velocity = pygame.math.Vector2(0, 0)
        self.angle = random.uniform(0, 360)
        self.angular_velocity = 0
        self.angular_acceleration = 0.8
        self.angular_friction = 0.85
        self.linear_friction = 0.99

        self.normal_speed_max = 8.5
        self.normal_accel = 0.16
        self.boost_speed_max = 19.0
        self.boost_accel = 0.65

        self.ogień_zza_rakiety = blue_fire_frames
        self.fire_anim_index = 0
        self.fire_anim_speed = 0.3

        self.is_boosting = False
        self.boost_timer = 0.0
        self.boost_cooldown_timer = 0.0
        self.boost_max_duration = 3.5
        self.boost_cooldown_time = 5.0

        self.trail_points = [] 
        self.is_thrusting = False

        self.weapons = [
            [self.ship_frames["images/Lasers/laserRed01.png"], 40, 5, 0.6],
            [self.ship_frames["images/Lasers/laserRed02.png"], 50, 3, 0.5],
            [self.ship_frames["images/Lasers/laserRed03.png"], 60, 2, 0.4]
        ]
        self.current_weapon = random.randint(0, len(self.weapons) - 1)
        self.weapon_timers = [0.0 for _ in range(len(self.weapons))]

    def death(self):
        if not self.is_dead:
            self.is_dead = True
            if self.music_obj:
                self.music_obj.play("images/audio/sfx_exp_medium4.wav", 0.2)
            colors = [(0, 150, 255), (80, 80, 255), (40, 40, 40), (200, 200, 255)]
            for _ in range(random.randint(12, 18)):
                self.debris_list.append(Debris(self.pos, self.velocity, random.choice(colors)))

    def update(self, dt: float):
        if self.is_dead:
            for d in self.debris_list: d.update()
            self.debris_list = [d for d in self.debris_list if d.life > 0]
            return

        if self.boost_cooldown_timer > 0: self.boost_cooldown_timer -= dt
        if self.is_boosting:
            self.boost_timer -= dt
            if self.boost_timer <= 0: self.is_boosting = False

        # --- LOGIKA AI I OMIJANIE PRZESZKÓD ---
        dir_to_player = (self.player_ref.player_pos - self.pos)
        dist_to_player = dir_to_player.length() or 1
        
        # 1. Omijanie asteroid
        avoidance_vector = pygame.math.Vector2(0, 0)
        danger_imminent = False 
        
        for asteroid in self.asteroid_manager.asteroids:
            dist_to_ast = self.pos.distance_to(asteroid.pos)
            if dist_to_ast < asteroid.radius + 450:
                diff = self.pos - asteroid.pos
                force = (1.0 - (dist_to_ast / (asteroid.radius + 450)))
                avoidance_vector += diff.normalize() * force * 7.0
                danger_imminent = True

        # 2. NOWOŚĆ: Omijanie innych wrogów (Separacja)
        neighbor_dist = 250  # Zasięg "widzenia" innych wrogów
        for other in self.manager.enemies:
            if other == self or other.is_dead:
                continue
            dist_to_enemy = self.pos.distance_to(other.pos)
            if dist_to_enemy < neighbor_dist:
                diff = self.pos - other.pos
                # Im bliżej siebie są wrogowie, tym gwałtowniej od siebie uciekają
                force = (1.0 - (dist_to_enemy / neighbor_dist)) ** 2
                avoidance_vector += diff.normalize() * force * 12.0
                danger_imminent = True

        # 3. Granica mapy
        dist_from_center = self.pos.length()
        if dist_from_center > self.manager.world_radius:
            self.death()
            return
        is_near_border = dist_from_center > (self.manager.world_radius - 600)
        
        # Decyzja o kierunku
        if is_near_border:
            target_dir = -self.pos
        else:
            target_dir = dir_to_player

        # Łączenie wektorów (Cel + Omijanie)
        combined_dir = target_dir.normalize()
        if avoidance_vector.length() > 0:
            combined_dir = (combined_dir + avoidance_vector).normalize()
            self.is_thrusting = True 
        else:
            self.is_thrusting = dist_to_player > 380

        target_angle = -math.degrees(math.atan2(combined_dir.y, combined_dir.x))

        # --- FIZYKA OBROTU I RUCHU ---
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        if angle_diff > 2: self.angular_velocity += self.angular_acceleration
        elif angle_diff < -2: self.angular_velocity -= self.angular_acceleration
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        if not self.is_boosting and self.boost_cooldown_timer <= 0:
            # Nie boostuj, jeśli jesteś w trakcie manewru omijania innych wrogów (zwiększa sterowność)
            if (dist_to_player > 750 or is_near_border) and abs(angle_diff) < 25 and not danger_imminent:
                self.is_boosting = True
                self.boost_timer = self.boost_max_duration
                self.boost_cooldown_timer = self.boost_cooldown_time

        max_v = self.boost_speed_max if self.is_boosting else self.normal_speed_max
        accel = self.boost_accel if self.is_boosting else self.normal_accel

        rad = math.radians(-self.angle)
        forward = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        
        if self.is_thrusting:
            self.velocity += forward * accel
            # (Animacja ognia i smug - bez zmian)
            anim_mult = 1.8 if self.is_boosting else 1.0
            self.fire_anim_index = (self.fire_anim_index + self.fire_anim_speed * anim_mult) % len(self.ogień_zza_rakiety)
            scale_factor = 1.0 if self.is_boosting else 0.65
            current_f_img = self.ogień_zza_rakiety[int(self.fire_anim_index)]
            if not self.is_boosting:
                w, h = current_f_img.get_size()
                current_f_img = pygame.transform.scale(current_f_img, (int(w * scale_factor), int(h * scale_factor)))
            rot_fire = pygame.transform.rotate(current_f_img, self.angle)
            dist_from_ship = -32 if self.is_boosting else -20
            fire_pos_offset = pygame.math.Vector2(dist_from_ship, 0).rotate(-self.angle)
            self.trail_points.append({
                "pos": self.pos + fire_pos_offset,
                "img": rot_fire, 
                "size": rot_fire.get_size(), 
                "life": 22.0 if self.is_boosting else 12.0,
                "max_life": 22.0 if self.is_boosting else 12.0
            })

        self.velocity *= self.linear_friction
        if self.velocity.length() > max_v:
            self.velocity.scale_to_length(max_v)
        self.pos += self.velocity

        for p in self.trail_points[:]:
            p["life"] -= 1.0
            if p["life"] <= 0: self.trail_points.remove(p)

        for i in range(len(self.weapon_timers)): self.weapon_timers[i] += dt
        if abs(angle_diff) < 25 and dist_to_player < 850 and not danger_imminent:
            self.shoot()

    def shoot(self):
        # ... (bez zmian) ...
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
            if self.music_obj:
                self.music_obj.play("images/audio/sfx_laser2.wav", 0.3)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        # ... (bez zmian) ...
        if self.is_dead:
            for d in self.debris_list: d.draw(window, camera_x, camera_y)
            return
        for p in self.trail_points:
            ratio = p["life"] / p["max_life"]
            sz = (int(p["size"][0] * ratio), int(p["size"][1] * ratio))
            if sz[0] > 0 and sz[1] > 0:
                r_img = pygame.transform.scale(p["img"], sz)
                r_img.set_alpha(int(160 * ratio))
                window.blit(r_img, r_img.get_rect(center=(p["pos"].x - camera_x, p["pos"].y - camera_y)))
        if self.is_thrusting:
            f_img = self.ogień_zza_rakiety[int(self.fire_anim_index)]
            if not self.is_boosting:
                w, h = f_img.get_size()
                f_img = pygame.transform.scale(f_img, (int(w * 0.65), int(h * 0.65)))
            f_rot = pygame.transform.rotate(f_img, self.angle)
            d_off = -32 if self.is_boosting else -20
            f_off = pygame.math.Vector2(d_off, 0).rotate(-self.angle)
            window.blit(f_rot, f_rot.get_rect(center=(int(self.pos.x - camera_x + f_off.x), int(self.pos.y - camera_y + f_off.y))))
        rotated_ship = pygame.transform.rotate(self.image, self.angle)
        rect = rotated_ship.get_rect(center=(self.pos.x - camera_x, self.pos.y - camera_y))
        window.blit(rotated_ship, rect.topleft)

class EnemyManager:
    def __init__(self, ship_frames: dict, player_ref: "SpaceShip", music_obj: "MusicManager", max_enemies: int, 
                 shoot_obj: "Shoot", world_radius: int, asteroid_manager: "AsteroidManager"):
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.music_obj = music_obj
        self.shoot_obj = shoot_obj
        self.max_enemies = max_enemies
        self.world_radius = world_radius
        self.asteroid_manager = asteroid_manager
        self.enemies = []

        # PRE-GENERACJA NIEBIESKIEGO OGNIA
        self.blue_fire_frames = []
        fire_paths = [f"images/dym/Explosion/explosion0{i}.png" for i in range(9)]
        for path in fire_paths:
            if path in self.ship_frames:
                surf = self.ship_frames[path].copy().convert_alpha()
                w, h = surf.get_size()
                # Manipulacja kanałami kolorów dla uzyskania niebieskiego płomienia
                for x in range(w):
                    for y in range(h):
                        r, g, b, a = surf.get_at((x, y))
                        if a > 0:
                            surf.set_at((x, y), (b, g, r, a))
                self.blue_fire_frames.append(pygame.transform.scale(surf, (int(w * 0.12), int(h * 0.10))))

    def update(self, dt: float):
        living = [e for e in self.enemies if not e.is_dead]
        
        # Spawning
        if len(living) < self.max_enemies and random.random() < 0.02:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(1100, 1400)
            spawn_pos = self.player_ref.player_pos + pygame.math.Vector2(math.cos(angle)*dist, math.sin(angle)*dist)
            
            if spawn_pos.length() < self.world_radius - 250:
                self.enemies.append(Enemy(self.ship_frames, self.player_ref, self.music_obj, 
                                        self.shoot_obj, self, spawn_pos, self.asteroid_manager, 
                                        self.blue_fire_frames))

        for enemy in self.enemies[:]:
            enemy.update(dt)
            # Usuwanie wrogów po zakończeniu animacji zniszczenia
            if enemy.is_dead and not enemy.debris_list:
                self.enemies.remove(enemy)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        for enemy in self.enemies:
            enemy.draw(window, camera_x, camera_y)