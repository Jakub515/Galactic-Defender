import pygame
import math
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from utils.music import MusicManager
    from jednostki.shoot import Shoot
    from jednostki.enemy_ship.enemy_manager import EnemyManager
    from .ship import SpaceShip
    from .parameters import Parameters

class Battle():
    def __init__(self, player_main_class: "SpaceShip", ship_frames: dict, ship_audio_path: list | tuple, cxx: int, cyy: int, player_pos: list | tuple, music: "MusicManager", shoot_obj: "Shoot", parameters: "Parameters"):
        self.parameters = parameters
        self.shoot_obj = shoot_obj
        self.music_obj = music
        self.ship_frames = ship_frames
        self.ship_audio_path = ship_audio_path
        self.player_main_class = player_main_class

        # --- DYNAMICZNE WCZYTYWANIE BRONI ---
        self.weapon_timers = [w[3] for w in parameters.weapons] 
        self.weapon_timers_2 = [w[3] for w in parameters.weapons_2]
        
        self.current_weapon = 0
        self.active_set = 1
        self.want_to_shoot = False
        self.switch_cooldown = 0.0

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
        self.shield_cooldown = 0.0

        # --- TARGETING SYSTEM ---
        self.tryb_naprowadzania = 0
        self.enemy_selected = None # ID dla pocisków
        self.chosen_enemy: Optional[Any] = None # Cały obiekt dla UI

    @property
    def max_switch_time(self): return self.parameters.max_switch_time

    @property
    def max_shield_cooldown(self): return self.parameters.max_shield_cooldown

    @property
    def shield_max_timer(self): return self.parameters.shield_max_timer

    @property
    def weapons(self): return self.parameters.weapons

    @property
    def weapons_2(self): return self.parameters.weapons_2

    def fire(self, active: bool): 
        if not self.player_main_class.is_destroyed: self.want_to_shoot = active

    def switch_weapon_set(self):
        if not self.player_main_class.is_destroyed and self.switch_cooldown <= 0:
            self.active_set = 2 if self.active_set == 1 else 1
            self.current_weapon = 0
            self.switch_cooldown = self.max_switch_time

    def select_weapon(self, index: int):
        if not self.player_main_class.is_destroyed:
            limit = len(self.weapons) if self.active_set == 1 else len(self.weapons_2)
            if index < limit: self.current_weapon = index

    def activate_shield(self, timer: int = 250):
        if not self.player_main_class.is_destroyed:
            if not self.shield_active and self.shield_cooldown <= 0:
                self.shield_active = True
                self.shield_timer = timer
                self.shield_cooldown = self.max_shield_cooldown

    def _handle_shooting(self, forward_dir: pygame.math.Vector2):
        if self.player_main_class.is_destroyed or self.switch_cooldown > 0:
            return

        w_set = self.weapons if self.active_set == 1 else self.weapons_2
        timers = self.weapon_timers if self.active_set == 1 else self.weapon_timers_2
        
        # Sprawdzenie cooldownu danej broni
        if timers[self.current_weapon] < w_set[self.current_weapon][3]:
            return

        w_data = w_set[self.current_weapon]
        timers[self.current_weapon] = 0.0
        
        bullet_vel = self.player_main_class.velocity + (forward_dir * w_data[1])
        
        shot_data = {
            "pos": self.player_main_class.player_pos.copy(), 
            "vel": bullet_vel, 
            "img": w_data[0], 
            "damage": w_data[2], 
            "dir": self.player_main_class.angle,
            "is_player_shooting": True,
            "destination": self.enemy_selected if self.active_set == 2 else None,
            "max-speed": w_data[4],
            "time-alive-all": w_data[-1] # Ostatni element to zazwyczaj czas życia
        }

        if self.active_set == 1: # Lasery
            shot_data["rocket"] = False
        else: # Rakiety
            shot_data.update({
                "rocket": True,
                "time-alive_before_manewring": w_data[5], 
                "time-alive-all": w_data[6],
                "steer-limit": w_data[7]
            })

        self.shoot_obj.create_missle(shot_data)
        
        if self.music_obj:
            self.music_obj.play("./data/images/audio/sfx_laser1.wav", 0.7)

    def update(self, dt: float, enemy_manager: "EnemyManager"):
        if self.switch_cooldown > 0:
            self.switch_cooldown -= dt

        # Obsługa tarczy
        if self.shield_active:
            self.shield_angle += 25
            self.shield_timer -= 1
            if self.shield_timer <= 0: self.shield_active = False
        elif self.shield_cooldown > 0:
            self.shield_cooldown = max(0, self.shield_cooldown - dt)

        # Update cooldownów broni
        for i in range(len(self.weapon_timers)): self.weapon_timers[i] += dt
        for i in range(len(self.weapon_timers_2)): self.weapon_timers_2[i] += dt

        # --- LOGIKA NAMIERZANIA ---
        self._find_target(enemy_manager)

        if self.want_to_shoot: 
            self._handle_shooting(self.player_main_class.forward_dir)

    def _find_target(self, enemy_manager: "EnemyManager"):
        if self.tryb_naprowadzania == 0:
            self.enemy_selected = None
            self.chosen_enemy = None
            return

        enemies = enemy_manager.enemies
        # Filtrujemy tylko żywych wrogów
        active_enemies = [e for e in enemies if not getattr(e, 'is_dead', False)]

        if not active_enemies:
            self.enemy_selected = None
            self.chosen_enemy = None
            return

        player_pos = pygame.math.Vector2(self.player_main_class.player_pos)
        best_target = None

        if self.tryb_naprowadzania == 1:
            # TRYB 1: Najbliższy
            min_dist = float('inf')
            for enemy in active_enemies:
                dist = player_pos.distance_to(enemy.pos)
                if dist < min_dist:
                    min_dist = dist
                    best_target = enemy

        elif self.tryb_naprowadzania == 2:
            # TRYB 2: Kątowy (przed statkiem)
            look_dir = self.player_main_class.forward_dir.normalize()
            max_score = -float('inf')
            max_radar_dist = 2500 

            for enemy in active_enemies:
                enemy_vec = pygame.math.Vector2(enemy.pos) - player_pos
                dist = enemy_vec.length()
                if dist > max_radar_dist: continue

                enemy_dir_normalized = enemy_vec.normalize()
                alignment = look_dir.dot(enemy_dir_normalized) # 1.0 = idealnie przed nami

                if alignment > 0.5: # Tylko wrogowie w stożku 60 stopni
                    score = (alignment * 1500) - (dist / 5)
                    if score > max_score:
                        max_score = score
                        best_target = enemy

        # Zapisujemy wyniki
        if best_target:
            self.chosen_enemy = best_target
            self.enemy_selected = best_target.id
        else:
            self.chosen_enemy = None
            self.enemy_selected = None

    def draw(self, window: pygame.Surface, draw_x: float, draw_y: float):
        if self.shield_active and not self.player_main_class.hp <= 0:
            frame_idx = (self.shield_timer // 3) % 3
            s_rot = pygame.transform.rotate(self.shield_frames[frame_idx], self.shield_angle)
            s_rot.set_alpha(150)
            window.blit(s_rot, s_rot.get_rect(center=(draw_x, draw_y)))

    def _create_placeholder_shield(self, radius: float, color: tuple | list):
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (radius, radius), radius, 3)
        return s
    
    def enemy_choose(self, tryb: int):
        """Metoda wywoływana przez klawisze R/T lub kliknięcie w UI"""
        self.tryb_naprowadzania = tryb
        return self.chosen_enemy # Zwraca aktualny cel dla UI