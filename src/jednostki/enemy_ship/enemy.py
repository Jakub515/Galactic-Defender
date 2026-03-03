import pygame
import math
import random
from .debris import Debris
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.music import MusicManager
    from shoot import Shoot
    from asteroids import AsteroidManager
    from space_ship import SpaceShip
    from .enemy_manager import EnemyManager

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
        self.delete_now = False
        self.end_of_level_flag = False

    def death(self):
        if not self.is_dead:
            self.is_dead = True
            if self.music_obj:
                self.music_obj.play("./data/images/audio/sfx_exp_medium4.wav", 0.2)
            colors = [(0, 150, 255), (80, 80, 255), (40, 40, 40), (200, 200, 255)]
            for _ in range(random.randint(12, 18)):
                self.debris_list.append(Debris(self.pos, self.velocity, random.choice(colors)))

    def update(self, dt: float):
        if self.hp <= 0 and not self.is_dead:
            self.death()
            
        if self.end_of_level_flag == True:
            self.delete_now = True
            self.hp = 0 
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
        
        if not is_rocket:
            # LASER (weapon_info indeksy 0-5)
            self.shoot_obj.create_missle({
                "pos": self.pos.copy(), 
                "vel": bullet_vel, 
                "img": weapon_info[0], 
                "damage": weapon_info[2], 
                "dir": self.angle,
                "rocket": False,
                "enemy_id": self.id,
                "is_enemy_shot": True,
                "destination": None,
                "time-alive-all": weapon_info[4],
                "max-speed": weapon_info[5]
            })
        else:
            # RAKIETA (weapon_info indeksy 0-7)
            self.shoot_obj.create_missle({
                "pos": self.pos.copy(),
                "vel": bullet_vel,
                "img": weapon_info[0],
                "damage": weapon_info[2],
                "dir": self.angle,
                "rocket": True,
                "is_enemy_shot": True,
                "enemy_id": self.id,
                "destination": self.player_ref,
                "max-speed": weapon_info[4],                   # Poprawiony indeks z 5 na 4
                "time-alive_before_manewring": weapon_info[5], # Poprawny indeks 5
                "time-alive-all": weapon_info[6],              # Poprawny indeks 6
                "steer-limit": weapon_info[7]                  # Poprawny indeks 7
            })
        if self.music_obj:
            if is_rocket:
                self.music_obj.play("./data/images/audio/z_opengameart/launches/flaunch.mp3", 0.15)
            else:
                self.music_obj.play("./data/images/audio/sfx_laser1.wav", 0.25, sound_is_laser=True)

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
        
    def end_of_level(self):
        self.end_of_level_flag = True