import pygame
import math
import random
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

        # --- OSŁONY ---
        try:
            self.shield_frames = [
                self.ship_frames["images/Effects/shield1.png"],
                self.ship_frames["images/Effects/shield2.png"],
                self.ship_frames["images/Effects/shield3.png"]
            ]
        except KeyError:
            self.shield_frames = [self._create_placeholder_shield(r, (100, 200, 255)) for r in [50, 55, 60]]          

        # --- SYSTEM BRONI ---
        self.weapons = [
            [self.ship_frames["images/Lasers/laserBlue12.png"], 60, 5,   0.1],
            [self.ship_frames["images/Lasers/laserBlue13.png"], 65, 4,   0.4],
            [self.ship_frames["images/Lasers/laserBlue14.png"], 70, 3,   0.3],
            [self.ship_frames["images/Lasers/laserBlue15.png"], 75, 2,   0.2],
            [self.ship_frames["images/Lasers/laserBlue16.png"], 80, 1,   0.1]
        ]
        self.weapons_2 = [
            [self.ship_frames["images/Missiles/spaceMissiles_001.png"], 1.5, 5,   3],
            [self.ship_frames["images/Missiles/spaceMissiles_004.png"], 1.5, 10,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_007.png"], 1.5, 15,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_010.png"], 1.5, 20,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_013.png"], 1.5, 25,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_016.png"], 1.5, 30,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_019.png"], 1.5, 35,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_022.png"], 1.5, 40,  3],
            [self.ship_frames["images/Missiles/spaceMissiles_025.png"], 1.5, 45,  3]
        ]
        self.weapon_timers = [0.0] * len(self.weapons)
        self.weapon_timers_2 = [0.0] * len(self.weapons_2)
        self.current_weapon = 0
        self.active_set = 1

        # --- OSŁONY ---
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
        self.shield_angle = 0 

    def _create_placeholder_shield(self, radius:float, color:tuple|list):
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (radius, radius), radius, 3)
        return s

    def fire(self, active:bool): 
        if not self.player_main_class.is_destroyed: self.want_to_shoot = active

    def switch_weapon_set(self):
        if not self.player_main_class.is_destroyed:
            self.active_set = 2 if self.active_set == 1 else 1
            self.current_weapon = 0

    def select_weapon(self, index:int):
        if not self.player_main_class.is_destroyed:
            limit = len(self.weapons) if self.active_set == 1 else len(self.weapons_2)
            if index < limit: self.current_weapon = index

    def activate_shield(self, timer:int=250):
        if not self.player_main_class.is_destroyed:
            self.shield_active = True
            self.shield_timer = timer

    # --- LOGIKA ---
    def _handle_shooting(self, forward_dir:pygame.math.Vector2):
        w_set = self.weapons if self.active_set == 1 else self.weapons_2
        timers = self.weapon_timers if self.active_set == 1 else self.weapon_timers_2
        
        if self.current_weapon < len(w_set):
            w_data = w_set[self.current_weapon]
            if timers[self.current_weapon] >= w_data[3]:
                timers[self.current_weapon] = 0.0
                
                # Prędkość pocisku = pęd statku + prędkość bazowa
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
        if self.shield_active:
            self.shield_angle += 25
            self.shield_timer -= 1
            if self.shield_timer <= 0: self.shield_active = False

        for i in range(len(self.weapon_timers)): self.weapon_timers[i] += dt
        for i in range(len(self.weapon_timers_2)): self.weapon_timers_2[i] += dt
        if self.want_to_shoot: self._handle_shooting(self.player_main_class.forward_dir)

        return [self.player_main_class.player_pos.x, self.player_main_class.player_pos.y]

    def draw(self, window:pygame.Surface, draw_x:float, draw_y:float):
        if self.shield_active:
            s_rot = pygame.transform.rotate(self.shield_frames[(self.shield_timer//3)%3], self.shield_angle)
            s_rot.set_alpha(150)
            window.blit(s_rot, s_rot.get_rect(center=(draw_x, draw_y)))

class SpaceShip():
    def __init__(self, ship_frames: dict, ship_audio_path:list|tuple, cxx:int, cyy:int, player_pos:list|tuple, music: "MusicManager", shoot_obj: "Shoot"):
        self.shoot_obj = shoot_obj
        self.music_obj = music
        self.ship_frames = ship_frames
        self.ship_audio_path = ship_audio_path
        
        # --- STAN ZNISZCZENIA ---
        self.is_destroyed = False
        self.debris_particles = []  # Fizyczne kawałki statku
        self.particles = []         # Iskry i dym
        self.explosion_flash = 0    # Biały rozbłysk na ekranie

        # --- GRAFIKA PODSTAWOWA ---
        self.original_image = self.ship_frames["images/space_ships/playerShip1_blue.png"]
        self.actual_frame = pygame.transform.rotate(self.original_image, -90)
        
        # --- ANIMACJA OGNIA ---
        fire_paths = [f"images/dym/Explosion/explosion0{i}.png" for i in range(9)]
        self.ogień_zza_rakiety = []
        for path in fire_paths:
            img = self.ship_frames[path]
            new_size = (int(img.get_width() * 0.15), int(img.get_height() * 0.12))
            self.ogień_zza_rakiety.append(pygame.transform.scale(img, new_size))
            
        self.fire_anim_index = 0
        self.fire_anim_speed = 0.3

        # --- SYSTEM SMUGI (TRAIL) ---
        self.trail_points = []  
        self.trail_max_life = 18
        self.last_trail_pos = pygame.math.Vector2(player_pos)

        # --- FLAGI STEROWANIA ---
        self.is_thrusting = False
        self.is_braking = False
        self.is_boosting = False
        self.rotation_dir = 0 
        self.want_to_shoot = False

        # --- FIZYKA ---
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

        self.hp = 100        

    # --- OBSŁUGA KATASTROFY ---
    def destroy_cause_collision(self):
        if self.is_destroyed:
            return
        return
        self.is_destroyed = True
        self.explosion_flash = 255 # Inicjalizacja mocnego błysku
        
        # 1. Tworzenie Odłamków (Debris) - większe kawałki kadłuba
        for _ in range(12):
            angle = random.uniform(0, 360)
            dist = random.uniform(2, 8)
            size = random.randint(10, 20)
            
            # Tworzenie "wycinka" z aktualnej grafiki statku
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.blit(self.actual_frame, (0, 0), (random.randint(0, 30), random.randint(0, 30), size, size))
            
            self.debris_particles.append({
                "pos": self.player_pos.copy(),
                "vel": pygame.math.Vector2(math.cos(math.radians(angle)), math.sin(math.radians(angle))) * dist + self.velocity,
                "angle": random.uniform(0, 360),
                "rot_speed": random.uniform(-15, 15),
                "img": surf,
                "life": random.randint(60, 120)
            })

        # 2. Tworzenie Iskier i Dymu (Particles)
        for _ in range(40):
            p_angle = random.uniform(0, 360)
            p_speed = random.uniform(1, 12)
            self.particles.append({
                "pos": self.player_pos.copy(),
                "vel": pygame.math.Vector2(math.cos(math.radians(p_angle)), math.sin(math.radians(p_angle))) * p_speed,
                "color": random.choice([(255, 200, 50), (255, 100, 0), (100, 100, 100)]),
                "radius": random.randint(2, 5),
                "life": random.randint(20, 50)
            })

        if self.music_obj:
            self.music_obj.handle_death()
            self.music_obj.play("images/audio/the_end_1.wav", 1.0)

    # --- INTERFEJS STEROWANIA ---
    def thrust(self, active:bool, boost:bool=False):
        if not self.is_destroyed:
            self.is_thrusting = active
            self.is_boosting = boost

    def rotate(self, direction:float): 
        if not self.is_destroyed: self.rotation_dir = direction

    def brake(self, active:bool): 
        if not self.is_destroyed: self.is_braking = active


    def update(self, dt:float):
        if self.is_destroyed:
            # Wygaszanie błysku
            if self.explosion_flash > 0:
                self.explosion_flash = max(0, self.explosion_flash - 10)
            
            # Aktualizacja odłamków statku
            self.player_pos += self.velocity
            self.velocity *= 0.97
            for d in self.debris_particles:
                d["pos"] += d["vel"]
                d["angle"] += d["rot_speed"]
                d["life"] -= 1
            self.debris_particles = [d for d in self.debris_particles if d["life"] > 0]
            
            # Aktualizacja cząsteczek (iskier)
            for p in self.particles:
                p["pos"] += p["vel"]
                p["life"] -= 1
                p["radius"] *= 0.96
            self.particles = [p for p in self.particles if p["life"] > 0]
            
            return [self.player_pos.x, self.player_pos.y]

        # 1. Rotacja
        if self.rotation_dir != 0:
            self.angular_velocity += self.rotation_dir * self.angular_acceleration
        self.angular_velocity *= self.angular_friction
        self.angle += self.angular_velocity

        # 2. Ruch liniowy i Korekta Driftu
        rad = math.radians(-self.angle)
        self.forward_dir = pygame.math.Vector2(math.cos(rad), math.sin(rad))

        if self.is_thrusting:
            accel_mult = 3.5 if self.is_boosting else 1.0
            self.velocity += self.forward_dir * (self.thrust_power * accel_mult)
            if self.velocity.length() > 1:
                target_vel = self.forward_dir * self.velocity.length()
                self.velocity = self.velocity.lerp(target_vel, self.drift_control)
        
        if self.is_braking: self.velocity *= self.braking_force
        
        curr_speed = self.velocity.length()
        max_v = self.boost_speed if self.is_boosting else self.max_speed
        self.velocity *= (self.speed_decay if curr_speed > max_v else self.linear_friction)
        self.player_pos += self.velocity

        # 3. System Smugi
        fire_offset = pygame.math.Vector2(-35, 0).rotate(-self.angle)
        current_fire_pos = self.player_pos + fire_offset
        if self.is_thrusting:
            anim_multiplier = 1.5 if self.is_boosting else 1.0
            self.fire_anim_index = (self.fire_anim_index + self.fire_anim_speed * anim_multiplier) % len(self.ogień_zza_rakiety)
            dist_vec = current_fire_pos - self.last_trail_pos
            step_size = 5 if self.is_boosting else 12 
            num_steps = int(dist_vec.length() // step_size)

            if num_steps > 0:
                raw_fire_img = self.ogień_zza_rakiety[int(self.fire_anim_index)]
                rotated_fire = pygame.transform.rotate(raw_fire_img, self.angle)
                for i in range(num_steps):
                    frac = (i + 1) / num_steps
                    interp_pos = self.last_trail_pos + dist_vec * frac
                    self.trail_points.append({
                        "pos": interp_pos, "img": rotated_fire, 
                        "size": rotated_fire.get_size(), "life": self.trail_max_life,
                        "max_life": self.trail_max_life
                    })
                self.last_trail_pos = current_fire_pos
        else:
            self.last_trail_pos = current_fire_pos

        for p in self.trail_points: p["life"] -= 1
        self.trail_points = [p for p in self.trail_points if p["life"] > 0]

        return [self.player_pos.x, self.player_pos.y]

    def draw(self, window:pygame.Surface, draw_x:float, draw_y:float):
        if self.is_destroyed:
            # Iskry
            for p in self.particles:
                rel_p = p["pos"] - self.player_pos
                pygame.draw.circle(window, p["color"], (int(draw_x + rel_p.x), int(draw_y + rel_p.y)), int(p["radius"]))
            
            # Odłamki
            for d in self.debris_particles:
                rel_offset = d["pos"] - self.player_pos
                rot_d = pygame.transform.rotate(d["img"], d["angle"])
                rot_d.set_alpha(max(0, min(255, d["life"] * 4)))
                window.blit(rot_d, rot_d.get_rect(center=(int(draw_x + rel_offset.x), int(draw_y + rel_offset.y))))
            
            # Błysk na całym ekranie
            if self.explosion_flash > 0:
                flash_surf = pygame.Surface((window.get_width(), window.get_height()))
                flash_surf.fill((255, 255, 255))
                flash_surf.set_alpha(self.explosion_flash)
                window.blit(flash_surf, (0,0))
            return

        # 1. Smuga
        for p in self.trail_points:
            life_ratio = p["life"] / p["max_life"]
            rel_offset = p["pos"] - self.player_pos
            scale = life_ratio * 0.9 
            new_size = (int(p["size"][0] * scale), int(p["size"][1] * scale))
            if new_size[0] > 0 and new_size[1] > 0:
                render_img = pygame.transform.scale(p["img"], new_size)
                render_img.set_alpha(int(180 * life_ratio))
                window.blit(render_img, render_img.get_rect(center=(int(draw_x + rel_offset.x), int(draw_y + rel_offset.y))))

        # 2. Główny ogień silnika
        if self.is_thrusting:
            f_img = self.ogień_zza_rakiety[int(self.fire_anim_index)]
            f_rot = pygame.transform.rotate(f_img, self.angle)
            f_off = pygame.math.Vector2(-35, 0).rotate(-self.angle)
            window.blit(f_rot, f_rot.get_rect(center=(int(draw_x + f_off.x), int(draw_y + f_off.y))))

        # 3. Statek
        ship_rot = pygame.transform.rotate(self.actual_frame, self.angle)
        window.blit(ship_rot, ship_rot.get_rect(center=(draw_x, draw_y)))