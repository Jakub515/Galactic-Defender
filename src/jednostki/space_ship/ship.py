import pygame
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.music import MusicManager
    from shoot import Shoot
    from src.jednostki.space_ship.parameters import Parameters
    
class SpaceShip():
    def __init__(self, ship_frames: dict, ship_audio_path:list|tuple, cxx:int, cyy:int, player_pos:list|tuple, music: "MusicManager", shoot_obj: "Shoot", parameters: "Parameters"):
        self.parameters = parameters
        
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
        self.player_x_start_pos = player_pos[0]
        self.player_y_start_pos = player_pos[1]
        self.player_pos = pygame.math.Vector2(self.player_x_start_pos, self.player_y_start_pos)
        self.velocity = pygame.math.Vector2(0, 0)  
        self.angle = 90                                     
        self.angular_velocity = 0                   
        self.angular_acceleration = 0.5            
        self.angular_friction = 0.90               
        self.max_angular_velocity = 7.0  

        # self.thrust_power = self.parameters.thrust_power               
        # self.max_speed = self.parameters.max_speed               
        # self.boost_speed = self.parameters.boost_speed
        # self.linear_friction = self.parameters.linear_friction              
        # self.braking_force = self.parameters.braking_force      
                    
        self.speed_decay = 0.96     
        self.drift_control = 0.05
        self.forward_dir = pygame.math.Vector2(0,0)

        # NOWE: System przegrzewania boosta
        self.boost_cooldown = 0.0
        # self.max_boost_cooldown = self.parameters.max_boost_cooldown
        self.is_boost_ready = True

        self.hp = self.parameters.hp  
        # self.max_hp = self.parameters.max_hp
        self.hp_timer = 0.0          # Licznik czasu
        self.hp_interval = 1.0       # Co ile sekund ma wystąpić akcja (1.0 = 1 sekunda)
        # self.hp_reg_speed = self.parameters.hp_reg_speed

        self.ship_rot = self.actual_frame
        
    def reinit_pos(self):
        # 1. Reset pozycji i fizyki ruchu
        self.player_pos = pygame.math.Vector2(self.player_x_start_pos, self.player_y_start_pos)
        self.velocity = pygame.math.Vector2(0, 0)
        
        # 2. Reset rotacji
        self.angle = 90
        self.angular_velocity = 0
        self.rotation_dir = 0
        
        # 3. Reset kierunku patrzenia (forward vector)
        rad = math.radians(-self.angle)
        self.forward_dir = pygame.math.Vector2(math.cos(rad), math.sin(rad))
        
        # 4. CZYSZCZENIE EFEKTÓW (Wizualne sprzątanie po "poprzednim życiu")
        self.trail_points = []
        self.debris_particles = []    # Czyścimy szczątki wybuchu
        self.particles = []           # Czyścimy inne cząsteczki
        self.last_trail_pos = self.player_pos.copy()
        self.explosion_flash = 0      # Reset błysku wybuchu
        
        # 5. REINICJALIZACJA STATUSÓW I ŻYCIA
        self.is_destroyed = False     # Przywrócenie do życia
        self.hp = self.max_hp         # Pełne HP
        self.hp_timer = 0.0           # Reset timera regeneracji
        
        # 6. Reset boosta
        self.boost_cooldown = 0.0
        self.is_boost_ready = True
        
        # 7. Reset flag sterowania
        self.is_thrusting = False
        self.is_braking = False
        self.is_boosting = False
        
    @property
    def linear_friction(self):
        return self.parameters.linear_friction
        
    @property
    def braking_force(self):
        return self.parameters.braking_force
        
    @property
    def max_boost_cooldown(self):
        return self.parameters.max_boost_cooldown
        
    @property
    def hp_reg_speed(self):
        return self.parameters.hp_reg_speed

    @property
    def max_hp(self):
        return self.parameters.max_hp

    @property
    def max_speed(self):
        return self.parameters.max_speed

    @property
    def boost_speed(self):
        return self.parameters.boost_speed

    @property
    def thrust_power(self):
        return self.parameters.thrust_power

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
        self.hp_timer += dt
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
        if (self.hp_timer >= self.hp_interval) and not self.is_destroyed:
            if self.hp < self.max_hp:
                self.hp += self.hp_reg_speed
            self.hp_timer -= self.hp_interval

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

        self.ship_rot = pygame.transform.rotate(self.actual_frame, self.angle)
        window.blit(self.ship_rot, self.ship_rot.get_rect(center=(draw_x, draw_y)))