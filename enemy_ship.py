import pygame
import math
import random
import json
from typing import TYPE_CHECKING
import random

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
        rect = pygame.Rect(self.pos.x - camera_x - s//2, self.pos.y - camera_y - s//2, s, s)
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        surf.fill((*self.color, alpha))
        window.blit(surf, rect)

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
        self.boost_speed_max = config["boost_speed"]
        self.boost_accel = config["boost_accel"]

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

        self.id = random.randint(0,100_000)

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

        if self.boost_cooldown_timer > 0: self.boost_cooldown_timer -= dt
        if self.is_boosting:
            self.boost_timer -= dt
            if self.boost_timer <= 0: self.is_boosting = False

        dir_to_player = (self.player_ref.player_pos - self.pos)
        dist_to_player = dir_to_player.length() or 1
        
        avoidance_vector = pygame.math.Vector2(0, 0)
        danger_imminent = False
        
        for asteroid in self.asteroid_manager.asteroids:
            dist_to_ast = self.pos.distance_to(asteroid.pos)
            if dist_to_ast < asteroid.radius + 450:
                diff = self.pos - asteroid.pos
                force = (1.0 - (dist_to_ast / (asteroid.radius + 450)))
                avoidance_vector += diff.normalize() * force * 7.0
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
            self.is_thrusting = dist_to_player > 380

        target_angle = -math.degrees(math.atan2(combined_dir.y, combined_dir.x))
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        if angle_diff > 2: self.angular_velocity += self.angular_acceleration
        elif angle_diff < -2: self.angular_velocity -= self.angular_acceleration
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        if not self.is_boosting and self.boost_cooldown_timer <= 0:
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
            anim_mult = 1.8 if self.is_boosting else 1.0
            self.fire_anim_index = (self.fire_anim_index + self.fire_anim_speed * anim_mult) % len(self.ogień_zza_rakiety)
            
            angle_idx = int(self.angle % 360)
            rot_fire = self.manager.fire_cache[int(self.fire_anim_index)][angle_idx]
            
            d_off = -32 if self.is_boosting else -20
            fire_pos_offset = pygame.math.Vector2(d_off, 0).rotate(-self.angle)
            self.trail_points.append({
                "pos": self.pos + fire_pos_offset, "img": rot_fire, "size": rot_fire.get_size(), 
                "life": 22.0 if self.is_boosting else 12.0, "max_life": 22.0 if self.is_boosting else 12.0
            })

        self.velocity *= self.linear_friction
        if self.velocity.length() > max_v: self.velocity.scale_to_length(max_v)
        self.pos += self.velocity

        for p in self.trail_points[:]:
            p["life"] -= 1.0
            if p["life"] <= 0: self.trail_points.remove(p)

        # LOGIKA STRZELANIA - POPRAWIONA
        self.weapon_timer += dt
        # Zasięg zwiększony do 2000 px, żeby rakiety miały sens
        if abs(angle_diff) < 25 and dist_to_player < 2000 and not danger_imminent:
            # Dystans przełączania: powyżej 450 rakiety, poniżej lasery
            if dist_to_player < 750:
                current_weapon = self.rocket_info
                is_rocket = True
            else:
                current_weapon = self.laser_info
                is_rocket = False
            
            if self.weapon_timer >= current_weapon[3]:
                self.shoot(current_weapon, is_rocket)

    def shoot(self, weapon_info: list, is_rocket: bool):
        self.weapon_timer = 0.0
        rad = math.radians(-self.angle)
        direction = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        
        # Prędkość wylotowa pocisku (weapon_info[1]) plus prędkość statku
        bullet_vel = self.velocity + (direction * weapon_info[1])
        
        self.shoot_obj.create_missle({
            "pos": self.pos.copy(),
            "vel": bullet_vel,
            "img": weapon_info[0],
            "damage": weapon_info[2],
            "dir": self.angle,
            "rocket": is_rocket,
            "is_enemy_shot": True,
            "enemy_id": self.id
        })
        
        if self.music_obj:
            sfx = "images/audio/sfx_laser2.wav" if is_rocket else "images/audio/sfx_laser1.wav"
            self.music_obj.play(sfx, 0.3)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        if self.is_dead:
            for d in self.debris_list: d.draw(window, camera_x, camera_y)
            return
            
        for p in self.trail_points:
            ratio = p["life"] / p["max_life"]
            sz = (int(p["size"][0] * ratio), int(p["size"][1] * ratio))
            if sz[0] > 1 and sz[1] > 1:
                r_img = pygame.transform.scale(p["img"], sz)
                r_img.set_alpha(int(160 * ratio))
                window.blit(r_img, r_img.get_rect(center=(p["pos"].x - camera_x, p["pos"].y - camera_y)))
        
        if self.is_thrusting:
            angle_idx = int(self.angle % 360)
            f_rot = self.manager.fire_cache[int(self.fire_anim_index)][angle_idx]
            d_off = -32 if self.is_boosting else -20
            f_off = pygame.math.Vector2(d_off, 0).rotate(-self.angle)
            window.blit(f_rot, f_rot.get_rect(center=(int(self.pos.x - camera_x + f_off.x), int(self.pos.y - camera_y + f_off.y))))
            
        angle_idx = int(self.angle % 360)
        rotated_ship = self.manager.ship_cache[self.type_name][angle_idx]
        rect = rotated_ship.get_rect(center=(int(self.pos.x - camera_x), int(self.pos.y - camera_y)))
        window.blit(rotated_ship, rect)

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

        config_data = self._load_config("data_slownik.json")
        self.ENEMY_TYPES = config_data.get("enemy_types", {})

        self.ship_cache = {}
        self.ship_base_images = {}
        self._init_ship_cache()
        
        self.blue_fire_frames = self._init_fire_frames()
        self.fire_cache = [[] for _ in range(len(self.blue_fire_frames))]
        self._init_fire_cache()

        self._init_weapons()

    def _load_config(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}

    def _init_ship_cache(self):
        for name, config in self.ENEMY_TYPES.items():
            path = config["image_path"]
            if path in self.ship_frames:
                base_img = pygame.transform.rotate(self.ship_frames[path], -90)
                self.ship_base_images[name] = base_img
                self.ship_cache[name] = [pygame.transform.rotate(base_img, angle) for angle in range(360)]

    def _init_fire_frames(self):
        temp_frames = []
        fire_paths = [f"images/dym/Explosion/explosion0{i}.png" for i in range(9)]
        for path in fire_paths:
            if path in self.ship_frames:
                surf = self.ship_frames[path].copy().convert_alpha()
                w, h = surf.get_size()
                for x in range(w):
                    for y in range(h):
                        r, g, b, a = surf.get_at((x, y))
                        if a > 0: surf.set_at((x, y), (b, g, r, a))
                temp_frames.append(pygame.transform.scale(surf, (int(w * 0.12), int(h * 0.10))))
        return temp_frames

    def _init_fire_cache(self):
        for i, frame in enumerate(self.blue_fire_frames):
            for angle in range(360):
                self.fire_cache[i].append(pygame.transform.rotate(frame, angle))

    def _init_weapons(self):
        # [obrazek, prędkość wylotowa, obrażenia, cooldown]
        self.weapons_lasers = [
            [self.ship_frames["images/Lasers/laserBlue12.png"], 60, 5,   0.2],
            [self.ship_frames["images/Lasers/laserBlue13.png"], 65, 8,   0.4],
            [self.ship_frames["images/Lasers/laserBlue14.png"], 70, 12,  0.5]
        ]
        # PRĘDKOŚCI RAKIET ZWIĘKSZONE Z 1.5 NA 15-20
        self.weapons_rockets = [
            [self.ship_frames["images/Missiles/spaceMissiles_001.png"], 15, 20,  3.0],
            [self.ship_frames["images/Missiles/spaceMissiles_004.png"], 17, 30,  3.5],
            [self.ship_frames["images/Missiles/spaceMissiles_010.png"], 20, 50,  4.0]
        ]

    def update(self, dt: float):
        living = [e for e in self.enemies if not e.is_dead]
        if len(living) < self.max_enemies:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(1100, 1400)
            spawn_pos = self.player_ref.player_pos + pygame.math.Vector2(math.cos(angle)*dist, math.sin(angle)*dist)
            
            if spawn_pos.length() < self.world_radius - 250:
                type_name = random.choice(list(self.ENEMY_TYPES.keys()))
                config = self.ENEMY_TYPES[type_name]
                
                l_idx = min(config.get("laser", 1) - 1, len(self.weapons_lasers)-1)
                r_idx = min(config.get("rocket", 1) - 1, len(self.weapons_rockets)-1)

                weapon_data = {
                    "laser": self.weapons_lasers[max(0, l_idx)],
                    "rocket": self.weapons_rockets[max(0, r_idx)]
                }

                self.enemies.append(Enemy(type_name, config, self.ship_frames, self.player_ref, 
                                        self.music_obj, self.shoot_obj, self, spawn_pos, 
                                        self.asteroid_manager, self.blue_fire_frames, weapon_data))

        for enemy in self.enemies[:]:
            enemy.update(dt)
            if enemy.is_dead and not enemy.debris_list:
                self.enemies.remove(enemy)

    def draw(self, window: pygame.Surface, camera_x: float, camera_y: float):
        for enemy in self.enemies:
            enemy.draw(window, camera_x, camera_y)