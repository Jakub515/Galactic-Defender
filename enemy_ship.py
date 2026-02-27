import pygame
import math
import random
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicManager
    from shoot import Shoot
    from asteroids import AsteroidManager
    from space_ship import SpaceShip

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

class IDGenerator:
    _counter = 999
    @classmethod
    def get_new_id(cls):
        cls._counter += 1
        return cls._counter

class Enemy:
    def __init__(self, type_name: str, config: dict, ship_frames: dict, player_ref: "SpaceShip", 
                 music_obj: "MusicManager", shoot_obj: "Shoot", enemy_manager: "EnemyManager", 
                 spawn_pos: pygame.math.Vector2, asteroid_manager: "AsteroidManager", 
                 blue_fire_frames: list, weapon_data: dict):
        
        self.type_name = type_name
        self.manager = enemy_manager
        self.player_ref = player_ref
        self.music_obj = music_obj
        self.shoot_obj = shoot_obj
        self.asteroid_manager = asteroid_manager

        self.hp = config["hp"]
        self.normal_speed_max = config["speed"]
        self.normal_accel = config["accel"]
        self.boost_speed_max = config.get("boost_speed", config["speed"] * 1.5)
        self.boost_accel = config.get("boost_accel", config["accel"] * 2.0)

        self.is_dead = False
        self.debris_list = []
        self.pos = pygame.math.Vector2(spawn_pos)
        self.velocity = pygame.math.Vector2(0, 0)
        self.angle = random.uniform(0, 360)
        self.angular_velocity = 0
        self.angular_acceleration = 0.8
        self.angular_friction = 0.85
        self.linear_friction = 0.99

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

        self.laser_info = weapon_data["laser"]
        self.rocket_info = weapon_data["rocket"]
        self.weapon_timer = 0.0

        self.id = IDGenerator.get_new_id()

    def death(self):
        if not self.is_dead:
            self.is_dead = True
            if self.music_obj:
                self.music_obj.play("images/audio/sfx_exp_medium4.wav", 0.2)
            colors = [(0, 150, 255), (80, 80, 255), (40, 40, 40), (200, 200, 255)]
            for _ in range(random.randint(12, 18)):
                self.debris_list.append(Debris(self.pos, self.velocity, random.choice(colors)))

    def update(self, dt: float):
        if self.hp <= 0 and not self.is_dead:
            self.death()

        if self.is_dead:
            for d in self.debris_list: d.update()
            self.debris_list = [d for d in self.debris_list if d.life > 0]
            return

        # --- AI & RUCH (bez zmian) ---
        if self.boost_cooldown_timer > 0: self.boost_cooldown_timer -= dt
        
        dir_to_player = (self.player_ref.player_pos - self.pos)
        dist_to_player = dir_to_player.length() or 1
        
        avoidance_vector = pygame.math.Vector2(0, 0)
        danger_imminent = False
        
        for asteroid in self.asteroid_manager.asteroids:
            dist_to_ast = self.pos.distance_to(asteroid.pos)
            if dist_to_ast < asteroid.radius + 300:
                diff = self.pos - asteroid.pos
                force = (1.0 - (dist_to_ast / (asteroid.radius + 300)))
                avoidance_vector += diff.normalize() * force * 10.0
                danger_imminent = True

        dist_from_center = self.pos.length()
        if dist_from_center > self.manager.world_radius:
            self.death()
            return
        
        is_near_border = dist_from_center > (self.manager.world_radius - 600)
        target_dir = -self.pos if is_near_border else dir_to_player
        combined_dir = target_dir.normalize()
        
        if avoidance_vector.length() > 0:
            combined_dir = (combined_dir + avoidance_vector).normalize()
            self.is_thrusting = True
        else:
            self.is_thrusting = dist_to_player > 350

        target_angle = -math.degrees(math.atan2(combined_dir.y, combined_dir.x))
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        if angle_diff > 2: self.angular_velocity += self.angular_acceleration
        elif angle_diff < -2: self.angular_velocity -= self.angular_acceleration
        
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        if not self.is_boosting and self.boost_cooldown_timer <= 0:
            if (dist_to_player > 800 or is_near_border) and abs(angle_diff) < 20 and not danger_imminent:
                self.is_boosting = True
                self.boost_timer = self.boost_max_duration
                self.boost_cooldown_timer = self.boost_cooldown_time

        if self.is_boosting:
            self.boost_timer -= dt
            if self.boost_timer <= 0: self.is_boosting = False

        max_v = self.boost_speed_max if self.is_boosting else self.normal_speed_max
        accel = self.boost_accel if self.is_boosting else self.normal_accel
        
        rad = math.radians(-self.angle)
        forward = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        
        if self.is_thrusting:
            self.velocity += forward * accel
            anim_mult = 1.8 if self.is_boosting else 1.0
            self.fire_anim_index = (self.fire_anim_index + self.fire_anim_speed * anim_mult) % len(self.ogień_zza_rakiety)
            
            if random.random() > 0.3:
                d_off = -35 if self.is_boosting else -22
                fire_pos = self.pos + pygame.math.Vector2(d_off, 0).rotate(-self.angle)
                self.trail_points.append({
                    "pos": fire_pos, "life": 15.0 if self.is_boosting else 8.0, 
                    "max": 15.0 if self.is_boosting else 8.0, "angle": self.angle
                })

        self.velocity *= self.linear_friction
        if self.velocity.length() > max_v: self.velocity.scale_to_length(max_v)
        self.pos += self.velocity

        for p in self.trail_points[:]:
            p["life"] -= 1.0
            if p["life"] <= 0: self.trail_points.remove(p)

        # --- NOWA LOGIKA STRZELANIA (ZAMIANA LASER VS RAKIETA) ---
        self.weapon_timer += dt
        
        if dist_to_player < 3000:
            weapon_to_use = None
            is_rock = False

            # Szansa na LASER - maleje wraz z dystansem (im bliżej tym większa)
            # Przy 200px: 1 - 200/1000 = 0.8 (80% na laser)
            # Przy 1000px: 1 - 1000/1000 = 0 (0% na laser -> przechodzi do rakiet)
            laser_chance = 1.0 - (dist_to_player / 1000.0)
            
            # Próba wybrania LASERA (jeśli bot go posiada)
            if self.laser_info and random.random() < laser_chance:
                if abs(angle_diff) < 30:
                    weapon_to_use = self.laser_info
                    is_rock = False
            
            # Jeśli nie wybrano lasera (bo był za daleko lub losowanie nie wyszło), 
            # spróbuj wybrać RAKIETĘ (jeśli bot ją posiada)
            elif self.rocket_info:
                if abs(angle_diff) < 60:
                    weapon_to_use = self.rocket_info
                    is_rock = True

            # Wykonaj strzał
            if weapon_to_use and self.weapon_timer >= weapon_to_use[3]:
                self.shoot(weapon_to_use, is_rock)
                self.weapon_timer = 0

    def shoot(self, weapon_info: list, is_rocket: bool):
        self.weapon_timer = 0.0
        rad = math.radians(-self.angle)
        direction = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        bullet_vel = self.velocity + (direction * weapon_info[1])
        
        self.shoot_obj.create_missle({
            "pos": self.pos.copy(),
            "vel": bullet_vel, "img": weapon_info[0],
            "damage": weapon_info[2],
            "dir": self.angle,
            "rocket": is_rocket,
            "is_enemy_shot": True,
            "enemy_id": self.id,
            "destination": self.player_ref,
            "max-speed": 25
        })
        
        if self.music_obj:
            sfx = "images/audio/sfx_laser2.wav" if is_rocket else "images/audio/sfx_laser1.wav"
            self.music_obj.play(sfx, 0.25)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        if self.is_dead:
            for d in self.debris_list: d.draw(window, camera_x, camera_y)
            return

        # Rysowanie smugi (trail)
        for p in self.trail_points:
            ratio = p["life"] / p["max"]
            angle_idx = int(p["angle"] % 360)
            f_img = self.manager.fire_cache[int(self.fire_anim_index % len(self.ogień_zza_rakiety))][angle_idx]
            # Skalowanie w dół wraz z życiem
            scaled_f = pygame.transform.scale(f_img, (int(f_img.get_width()*ratio), int(f_img.get_height()*ratio)))
            scaled_f.set_alpha(int(150 * ratio))
            window.blit(scaled_f, scaled_f.get_rect(center=(p["pos"].x - camera_x, p["pos"].y - camera_y)))

        # Rysowanie ognia silnika bezpośrednio za statkiem
        if self.is_thrusting:
            angle_idx = int(self.angle % 360)
            f_img = self.manager.fire_cache[int(self.fire_anim_index)][angle_idx]
            d_off = -32 if self.is_boosting else -20
            f_off = pygame.math.Vector2(d_off, 0).rotate(-self.angle)
            window.blit(f_img, f_img.get_rect(center=(self.pos.x - camera_x + f_off.x, self.pos.y - camera_y + f_off.y)))

        # Rysowanie statku
        angle_idx = int(self.angle % 360)
        rotated_ship = self.manager.ship_cache[self.type_name][angle_idx]
        window.blit(rotated_ship, rotated_ship.get_rect(center=(int(self.pos.x - camera_x), int(self.pos.y - camera_y))))
class EnemyManager:
    def __init__(self, ship_frames, player_ref, music_obj, max_enemies, 
                 shoot_obj, world_radius, asteroid_manager):
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.music_obj = music_obj
        self.shoot_obj = shoot_obj
        self.max_enemies = max_enemies
        self.world_radius = world_radius
        self.asteroid_manager = asteroid_manager
        self.enemies: list[Enemy] = []

        # --- ŁADOWANIE KONFIGURACJI ---
        self.config_all = self._load_config("enemie_slownik.json")
        self.ENEMY_TYPES = self.config_all.get("enemy_types", {})

        # --- CACHE GRAFIKI ---
        self.ship_cache = {}
        self.ship_base_images = {}
        self._init_ship_cache()
        
        self.blue_fire_frames = self._init_fire_frames()
        self.fire_cache = [[] for _ in range(len(self.blue_fire_frames))]
        self._init_fire_cache()

        # --- SYSTEM BRONI (Listy indeksowane) ---
        self.weapons_lasers = []
        self.weapons_rockets = []
        self._init_weapons()

    def _load_config(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd ładowania JSON: {e}")
            return {}

    def _init_ship_cache(self):
        for name, config in self.ENEMY_TYPES.items():
            path = config.get("image_path")
            if path in self.ship_frames:
                # Rotacja o -90 dla grafik Kenneya
                base_img = pygame.transform.rotate(self.ship_frames[path], -90)
                self.ship_base_images[name] = base_img
                self.ship_cache[name] = [pygame.transform.rotate(base_img, angle) for angle in range(360)]

    def _init_fire_frames(self):
        temp_frames = []
        for i in range(9):
            path = f"images/dym/Explosion/explosion0{i}.png"
            if path in self.ship_frames:
                surf = self.ship_frames[path].copy().convert_alpha()
                for x in range(surf.get_width()):
                    for y in range(surf.get_height()):
                        r, g, b, a = surf.get_at((x, y))
                        if a > 0: surf.set_at((x, y), (b, g, r, a))
                temp_frames.append(pygame.transform.scale(surf, (20, 16)))
        return temp_frames

    def _init_fire_cache(self):
        for i, frame in enumerate(self.blue_fire_frames):
            for angle in range(360):
                self.fire_cache[i].append(pygame.transform.rotate(frame, angle))

    def _init_weapons(self):
        """Wczytuje bronie z 'enemy-weapon-data' do list."""
        w_data = self.config_all.get("enemy-weapon-data", {})
        
        # Lasery
        l_dict = w_data.get("lasers", {})
        # Sortujemy klucze laser1, laser2..., żeby indeksy się zgadzały
        for key in sorted(l_dict.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
            w = l_dict[key]
            img = self.ship_frames.get(w["path"])
            if img:
                self.weapons_lasers.append([img, w["speed"], w["damage"], w["cooldown"]])

        # Rakiety
        r_dict = w_data.get("rockets", {})
        for key in sorted(r_dict.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
            w = r_dict[key]
            img = self.ship_frames.get(w["path"])
            if img:
                self.weapons_rockets.append([img, w["speed"], w["damage"], w["cooldown"]])
        
        print(f"Zasoby broni załadowane: Lasery: {len(self.weapons_lasers)}, Rakiety: {len(self.weapons_rockets)}")

    def _get_random_weapon(self, bot_config, weapon_key, source_list):
        """Pobiera losową broń na podstawie indeksów z JSON."""
        indices = bot_config.get(weapon_key)
        
        # Jeśli False, None lub pusta lista w JSON
        if indices is False or indices is None or not source_list:
            return None
        
        try:
            # Obsługa listy [1, 2] lub pojedynczej liczby
            chosen_nr = random.choice(indices) if isinstance(indices, list) else indices
            
            # Konwersja na indeks listy (1-based -> 0-based)
            idx = max(0, min(int(chosen_nr) - 1, len(source_list) - 1))
            return source_list[idx]
        except (ValueError, TypeError, IndexError):
            return None

    def update(self, dt):
        living = [e for e in self.enemies if not e.is_dead]
        
        if len(living) < self.max_enemies:
            # Losowanie pozycji spawnu
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(1100, 1500)
            spawn_pos = self.player_ref.player_pos + pygame.math.Vector2(math.cos(angle)*dist, math.sin(angle)*dist)
            
            if spawn_pos.length() < self.world_radius - 300:
                type_name = random.choice(list(self.ENEMY_TYPES.keys()))
                bot_config = self.ENEMY_TYPES[type_name]
                
                # --- KLUCZOWA POPRAWKA: dopasowanie do Twojego JSON (laser/rocket bez 's') ---
                weapon_data = {
                    "laser": self._get_random_weapon(bot_config, "laser", self.weapons_lasers),
                    "rocket": self._get_random_weapon(bot_config, "rocket", self.weapons_rockets)
                }
                new_enemy = Enemy(type_name, bot_config, self.ship_frames, self.player_ref, 
                                 self.music_obj, self.shoot_obj, self, spawn_pos, 
                                 self.asteroid_manager, self.blue_fire_frames, weapon_data)
                self.enemies.append(new_enemy)

        for enemy in self.enemies[:]:
            enemy.update(dt)
            if enemy.is_dead and not enemy.debris_list:
                self.enemies.remove(enemy)

    def draw(self, window, camera_x, camera_y):
        for enemy in self.enemies:
            enemy.draw(window, camera_x, camera_y)

    def get_enemy_by_id(self,id) -> Enemy | None:
        for enemy in self.enemies:
            if enemy.id == id:
                return enemy
            
        return None