import pygame
import math
import random
import json  # Dodano import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicManager
    from shoot import Shoot

class Battle():
    def __init__(self, player_main_class: "SpaceShip", ship_frames: dict, ship_audio_path:list|tuple, cxx:int, cyy:int, player_pos:list|tuple, music: "MusicManager", shoot_obj: "Shoot"):
        self.shoot_obj = shoot_obj
        self.music_obj = music
        self.ship_frames = ship_frames
        self.ship_audio_path = ship_audio_path
        self.player_main_class = player_main_class

        # --- DYNAMICZNE WCZYTYWANIE BRONI ---
        self.weapons = []
        self.weapons_2 = []
        self._load_weapons_from_config("player_slownik.json") #
        
        # Inicjalizacja timerów na podstawie wczytanych danych (indeks 3 to cooldown)
        self.weapon_timers = [w[3] for w in self.weapons] #
        self.weapon_timers_2 = [w[3] for w in self.weapons_2] #
        
        self.current_weapon = 0
        self.active_set = 1
        self.want_to_shoot = False
        self.switch_cooldown = 0.0
        self.max_switch_time = 2.5 

        # --- OSŁONY I COOLDOWN ---
        try:
            self.shield_frames = [
                self.ship_frames["images/Effects/shield1.png"],
                self.ship_frames["images/Effects/shield2.png"],
                self.ship_frames["images/Effects/shield3.png"]
            ]
        except KeyError:
            self.shield_frames = [self._create_placeholder_shield(r, (100, 200, 255)) for r in [50, 55, 60]]
            
        self.shield_active = False
        self.shield_timer = 0 
        self.shield_max_timer = 250
        self.shield_angle = 0 
        self.shield_cooldown = 0.0
        self.max_shield_cooldown = 1.0

    def _load_weapons_from_config(self, filename: str):
        """Wczytuje definicje broni z sekcji player-weapon-data pliku JSON."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f) #
            
            weapon_data = config.get("player-weapon-data", {}) #

            # Wczytywanie laserów (Set 1)
            lasers = weapon_data.get("lasers", {}) #
            for key in sorted(lasers.keys(), key=lambda x: int(x.replace('laser', ''))): #
                w = lasers[key]
                img = self.ship_frames.get(w["path"]) #
                if img:
                    self.weapons.append([img, w["speed"], w["damage"], w["cooldown"]]) #

            # Wczytywanie rakiet (Set 2)
            rockets = weapon_data.get("rockets", {}) #
            for key in sorted(rockets.keys(), key=lambda x: int(x.replace('rocket', ''))): #
                w = rockets[key]
                img = self.ship_frames.get(w["path"]) #
                if img:
                    self.weapons_2.append([img, w["speed"], w["damage"], w["cooldown"]]) #

        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Exception(f"Błąd ładowania broni gracza: {e}") from e

    def fire(self, active:bool): 
        if not self.player_main_class.is_destroyed: self.want_to_shoot = active

    def switch_weapon_set(self):
        if not self.player_main_class.is_destroyed and self.switch_cooldown <= 0:
            self.active_set = 2 if self.active_set == 1 else 1
            self.current_weapon = 0
            self.switch_cooldown = self.max_switch_time

    def select_weapon(self, index:int):
        if not self.player_main_class.is_destroyed:
            limit = len(self.weapons) if self.active_set == 1 else len(self.weapons_2)
            if index < limit: self.current_weapon = index

    def activate_shield(self, timer:int=250):
        if not self.player_main_class.is_destroyed:
            if not self.shield_active and self.shield_cooldown <= 0:
                self.shield_active = True
                self.shield_timer = timer
                self.shield_max_timer = timer
                self.shield_cooldown = self.max_shield_cooldown

    def _handle_shooting(self, forward_dir:pygame.math.Vector2):
        if self.player_main_class.is_destroyed or self.switch_cooldown > 0:
            return

        w_set = self.weapons if self.active_set == 1 else self.weapons_2
        timers = self.weapon_timers if self.active_set == 1 else self.weapon_timers_2
        
        if any(timers[i] < w_set[i][3] for i in range(len(w_set))):
            return

        if self.current_weapon < len(w_set):
            w_data = w_set[self.current_weapon]
            timers[self.current_weapon] = 0.0
            
            bullet_vel = self.player_main_class.velocity + (forward_dir * w_data[1])
            self.shoot_obj.create_missle({
                "pos": self.player_main_class.player_pos.copy(), 
                "vel": bullet_vel, 
                "img": w_data[0], 
                "damage": w_data[2], 
                "dir": self.player_main_class.angle,
                "rocket": (self.active_set == 2)
            })
            if self.music_obj:
                self.music_obj.play("images/audio/sfx_laser1.wav", 0.7)

    def update(self, dt:float):
        if self.switch_cooldown > 0:
            self.switch_cooldown -= dt

        # Obsługa tarczy            
        if self.shield_active:
            self.shield_angle += 25
            self.shield_timer -= 1
            if self.shield_timer <= 0: 
                self.shield_active = False
        elif self.shield_cooldown > 0:
            self.shield_cooldown = max(0, self.shield_cooldown - dt)

        for i in range(len(self.weapon_timers)): self.weapon_timers[i] += dt
        for i in range(len(self.weapon_timers_2)): self.weapon_timers_2[i] += dt
        
        if self.want_to_shoot: self._handle_shooting(self.player_main_class.forward_dir)

    def draw(self, window:pygame.Surface, draw_x:float, draw_y:float):
        if self.shield_active and not self.player_main_class.hp <= 0:
            s_rot = pygame.transform.rotate(self.shield_frames[(self.shield_timer//3)%3], self.shield_angle)
            s_rot.set_alpha(150)
            window.blit(s_rot, s_rot.get_rect(center=(draw_x, draw_y)))

    def _create_placeholder_shield(self, radius:float, color:tuple|list):
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (radius, radius), radius, 3)
        return s

class SpaceShip():
    def __init__(self, ship_frames: dict, ship_audio_path:list|tuple, cxx:int, cyy:int, player_pos:list|tuple, music: "MusicManager", shoot_obj: "Shoot"):
        self.shoot_obj = shoot_obj
        self.music_obj = music
        self.ship_frames = ship_frames
        self.ship_audio_path = ship_audio_path
        
        self.is_destroyed = False
        self.debris_particles = []
        self.particles = []
        self.explosion_flash = 0

        self.original_image = self.ship_frames["images/space_ships/playerShip1_blue.png"]
        self.actual_frame = pygame.transform.rotate(self.original_image, -90)
        
        fire_paths = [f"images/dym/Explosion/explosion0{i}.png" for i in range(9)]
        self.ogień_zza_rakiety = []
        for path in fire_paths:
            img = self.ship_frames[path]
            new_size = (int(img.get_width() * 0.15), int(img.get_height() * 0.12))
            self.ogień_zza_rakiety.append(pygame.transform.scale(img, new_size))
            
        self.fire_anim_index = 0
        self.fire_anim_speed = 0.3

        self.trail_points = []  
        self.trail_max_life = 18
        self.last_trail_pos = pygame.math.Vector2(player_pos)

        self.is_thrusting = False
        self.is_braking = False
        self.is_boosting = False
        self.rotation_dir = 0 

        # --- FIZYKA I BOOST COOLDOWN ---
        self.player_pos = pygame.math.Vector2(player_pos[0], player_pos[1])
        self.velocity = pygame.math.Vector2(0, 0)  
        self.angle = 90                                     
        self.angular_velocity = 0                   
        self.angular_acceleration = 0.5            
        self.angular_friction = 0.90               
        self.max_angular_velocity = 7.0            
        self.thrust_power = 0.4                    
        self.max_speed = 10.0                      
        self.boost_speed = 22.0  
        self.linear_friction = 0.985               
        self.braking_force = 0.92                  
        self.speed_decay = 0.96     
        self.drift_control = 0.05
        self.forward_dir = pygame.math.Vector2(0,0)

        # NOWE: System przegrzewania boosta
        self.boost_cooldown = 0.0
        self.max_boost_cooldown = 50.0
        self.is_boost_ready = True

        self.hp = 100        

    def destroy_cause_collision(self):
        if self.is_destroyed: return
        self.hp = 0
        self.is_destroyed = True
        self.explosion_flash = 255
        for _ in range(12):
            size = random.randint(10, 20)
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.blit(self.actual_frame, (0, 0), (random.randint(0, 30), random.randint(0, 30), size, size))
            self.debris_particles.append({
                "pos": self.player_pos.copy(),
                "vel": pygame.math.Vector2(random.uniform(-1,1), random.uniform(-1,1)).normalize() * random.uniform(2,8) + self.velocity,
                "angle": random.uniform(0, 360), "rot_speed": random.uniform(-15, 15),
                "img": surf, "life": random.randint(60, 120)
            })
        if self.music_obj:
            self.music_obj.handle_death()

    def thrust(self, active:bool, boost:bool=False):
        if not self.is_destroyed:
            self.is_thrusting = active
            self.is_boosting = boost

    def rotate(self, direction:float): 
        if not self.is_destroyed: self.rotation_dir = direction

    def brake(self, active:bool): 
        if not self.is_destroyed: self.is_braking = active

    def update(self, dt:float):
        if self.hp <= 0:
            self.hp = 0
            self.destroy_cause_collision()
        if self.is_destroyed:
            self.explosion_flash = max(0, self.explosion_flash - 10)
            self.player_pos += self.velocity
            self.velocity *= 0.97
            for d in self.debris_particles:
                d["pos"] += d["vel"]; d["angle"] += d["rot_speed"]; d["life"] -= 1
            self.debris_particles = [d for d in self.debris_particles if d["life"] > 0]
            return [self.player_pos.x, self.player_pos.y]

        # Logika Boostera
        if self.is_thrusting and self.is_boosting and self.is_boost_ready:
            self.boost_cooldown += dt * 1.5
            if self.boost_cooldown >= self.max_boost_cooldown:
                self.is_boost_ready = False
        else:
            self.boost_cooldown = max(0, self.boost_cooldown - dt * 0.8)
            if self.boost_cooldown == 0: self.is_boost_ready = True

        can_boost = self.is_boosting and self.is_boost_ready

        if self.rotation_dir != 0:
            self.angular_velocity += self.rotation_dir * self.angular_acceleration
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        rad = math.radians(-self.angle)
        self.forward_dir = pygame.math.Vector2(math.cos(rad), math.sin(rad))

        if self.is_thrusting:
            accel_mult = 3.5 if can_boost else 1.0
            self.velocity += self.forward_dir * (self.thrust_power * accel_mult)
            if self.velocity.length() > 1:
                self.velocity = self.velocity.lerp(self.forward_dir * self.velocity.length(), self.drift_control)
        
        if self.is_braking: self.velocity *= self.braking_force
        
        max_v = self.boost_speed if can_boost else self.max_speed
        self.velocity *= (self.speed_decay if self.velocity.length() > max_v else self.linear_friction)
        self.player_pos += self.velocity

        # System Smugi
        fire_offset = pygame.math.Vector2(-35, 0).rotate(-self.angle)
        current_fire_pos = self.player_pos + fire_offset
        if self.is_thrusting:
            anim_mult = 1.5 if can_boost else 1.0
            self.fire_anim_index = (self.fire_anim_index + self.fire_anim_speed * anim_mult) % len(self.ogień_zza_rakiety)
            dist_vec = current_fire_pos - self.last_trail_pos
            step = 5 if can_boost else 12 
            num_steps = int(dist_vec.length() // step)
            if num_steps > 0:
                rot_fire = pygame.transform.rotate(self.ogień_zza_rakiety[int(self.fire_anim_index)], self.angle)
                for i in range(num_steps):
                    self.trail_points.append({
                        "pos": self.last_trail_pos + dist_vec * ((i+1)/num_steps), "img": rot_fire, 
                        "size": rot_fire.get_size(), "life": self.trail_max_life, "max_life": self.trail_max_life
                    })
                self.last_trail_pos = current_fire_pos
        else: self.last_trail_pos = current_fire_pos

        for p in self.trail_points: p["life"] -= 1
        self.trail_points = [p for p in self.trail_points if p["life"] > 0]
        return [self.player_pos.x, self.player_pos.y]

    def draw(self, window:pygame.Surface, draw_x:float, draw_y:float):
        if self.is_destroyed:
            for p in self.particles:
                pygame.draw.circle(window, p["color"], (int(draw_x + (p["pos"].x - self.player_pos.x)), int(draw_y + (p["pos"].y - self.player_pos.y))), int(p["radius"]))
            for d in self.debris_particles:
                rel = d["pos"] - self.player_pos
                rot_d = pygame.transform.rotate(d["img"], d["angle"])
                rot_d.set_alpha(max(0, min(255, d["life"] * 4)))
                window.blit(rot_d, rot_d.get_rect(center=(int(draw_x + rel.x), int(draw_y + rel.y))))
            return

        for p in self.trail_points:
            ratio = p["life"] / p["max_life"]
            rel = p["pos"] - self.player_pos
            sz = (int(p["size"][0] * ratio * 0.9), int(p["size"][1] * ratio * 0.9))
            if sz[0] > 0:
                r_img = pygame.transform.scale(p["img"], sz)
                r_img.set_alpha(int(180 * ratio))
                window.blit(r_img, r_img.get_rect(center=(int(draw_x + rel.x), int(draw_y + rel.y))))

        if self.is_thrusting:
            f_img = self.ogień_zza_rakiety[int(self.fire_anim_index)]
            f_rot = pygame.transform.rotate(f_img, self.angle)
            f_off = pygame.math.Vector2(-35, 0).rotate(-self.angle)
            window.blit(f_rot, f_rot.get_rect(center=(int(draw_x + f_off.x), int(draw_y + f_off.y))))

        ship_rot = pygame.transform.rotate(self.actual_frame, self.angle)
        window.blit(ship_rot, ship_rot.get_rect(center=(draw_x, draw_y)))