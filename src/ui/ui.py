import pygame
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jednostki.space_ship import Battle, Parameters, SpaceShip
    from jednostki.enemy_ship.enemy_manager import EnemyManager
    from core.event import Event
    from core.level_manager import LevelManager
    from utils.collisions import Collision

class GameController:
    def __init__(self, battle: "Battle", event_obj: "Event", player: "SpaceShip", cxx: int, cyy: int, loaded_images: dict, clock: pygame.time.Clock, level_manager: "LevelManager", collision: "Collision", enemy_manager: "EnemyManager", param: "Parameters"):
        self.ui = UI(event_obj, cxx, cyy, loaded_images, battle, player, level_manager, enemy_manager, param)
        self.input_handler = InputHandler(event_obj, player, battle, self.ui, collision, enemy_manager)
        self.clock = clock

    def update(self, dt: float):
        self.input_handler.update()
        self.ui.update(self.clock.get_fps(), dt)

    def draw(self, window: pygame.Surface, camera):
        self.ui.draw(window, camera)

class InputHandler:
    def __init__(self, event_obj: "Event", player_obj: "SpaceShip", player_shoot: "Battle", ui_obj: "UI", collision:"Collision", enemy_manager: "EnemyManager"):
        self.event_obj = event_obj
        self.player_obj = player_obj
        self.ctrl_pressed_last_frame = False
        self.player_shoot = player_shoot
        self.ui_obj = ui_obj
        self.collision = collision
        self.enemy_manager = enemy_manager
    
    def update(self):
        self.ui_obj.reward_1_choosed = self.event_obj.key_o
        self.ui_obj.reward_2_choosed = self.event_obj.key_p

        if self.event_obj.key_r:
            self.ui_obj.last_celowanie_mode = 1
        elif self.event_obj.key_t:
            self.ui_obj.last_celowanie_mode = 2
            
        if self.ui_obj.player_can_manevre:
            self.player_obj.thrust(self.event_obj.key_up, boost=self.event_obj.backquote)
            if self.event_obj.key_left: self.player_obj.rotate(1)
            elif self.event_obj.key_right: self.player_obj.rotate(-1)
            else: self.player_obj.rotate(0)
            self.player_obj.brake(self.event_obj.key_down)

            self.player_shoot.fire(self.event_obj.key_space)
            if self.event_obj.key_s: self.player_shoot.activate_shield()
            
        else:
            self.player_obj.thrust(False, boost=False)
            self.player_obj.brake(True)

            self.player_shoot.fire(self.event_obj.key_space)
            if self.event_obj.key_s: self.player_shoot.activate_shield()

        if self.event_obj.key_ctrl_left and not self.ctrl_pressed_last_frame:
            self.player_shoot.switch_weapon_set()
        self.ctrl_pressed_last_frame = self.event_obj.key_ctrl_left

        keys_numbers = [self.event_obj.key_1, self.event_obj.key_2, self.event_obj.key_3,
                        self.event_obj.key_4, self.event_obj.key_5, self.event_obj.key_6,
                        self.event_obj.key_7, self.event_obj.key_8, self.event_obj.key_9]
        for i, pressed in enumerate(keys_numbers):
            if pressed:
                self.player_shoot.select_weapon(i)
                break
        

class UI:
    def __init__(self, event_obj: "Event", screen_width: int, screen_height: int, images: dict, battle: "Battle", space_ship: "SpaceShip", level_manager: "LevelManager", enemy_manager: "EnemyManager", param: "Parameters"):
        self.event_obj = event_obj
        self.images = images
        self.battle = battle
        self.cxx = screen_width
        self.cyy = screen_height
        self.space_ship = space_ship
        self.level_manager = level_manager
        self.enemy_manager = enemy_manager
        self.space_ship_parameters = param
        
        self.displayed_hp = space_ship.hp
        self.max_hp = 100
        self.pulse_time = 0 

        self.displayed_xp = self.level_manager.xp
        
        try:
            self.font = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 14)
            self.font_big = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 18)
        except:
            self.font = pygame.font.SysFont("Arial", 14, bold=True)
            self.font_big = pygame.font.SysFont("Arial", 18, bold=True)

        self.laser_paths = ["images/Lasers/laserBlue12.png", "images/Lasers/laserBlue13.png", "images/Lasers/laserBlue14.png", "images/Lasers/laserBlue15.png", "images/Lasers/laserBlue16.png"]
        self.missile_paths = [f"images/Missiles/spaceMissiles_{p}.png" for p in ["001", "004", "007", "010", "013", "016", "019", "022", "025"]]

        self.fps = 0
        self.slot_size = 55
        self.spacing = 8
        self.y_pos = 25
        
        self.frame_x = screen_width // 2
        self.frame_vel = 0
        self.target_x = 0
        self.spring_k = 0.5
        self.friction = 0.4

        self.last_celowanie_mode = 1

        self.reward_1_choosed = False
        self.reward_2_choosed = False
        self.active_rewards: dict[str, dict[str, Any]] = {}  # Przechowuje (funkcja, tekst) dla obu nagród
        self.show_reward_selection = False
        
        self.reward_shown_timer = 0
        self.reward_shown_timer_delay = 1.0
        
        # Animacje nagród
        self.reward_alpha = 0  # Aktualna przezroczystość
        self.is_closing_rewards = False
        
        # Logika XP
        self.prev_max_xp = 0 # XP wymagane na poprzedni poziom
        self.displayed_xp = self.level_manager.xp
        
        self.player_can_manevre = True

    def get_hp_color(self, ratio):
        # Zabezpieczenie, aby ratio było w przedziale 0.0 - 1.0
        ratio = max(0.0, min(1.0, ratio))
        
        if ratio > 0.5:
            # Od zielonego (0, 255, 0) do żółtego (255, 255, 0)
            # Przy ratio=0.6, czerwony rośnie
            red = int(255 * (1 - ratio) * 2)
            return pygame.Color(red, 255, 0)
        else:
            # Od żółtego (255, 255, 0) do czerwonego (255, 0, 0)
            # Przy ratio=0.4, zielony maleje
            green = int(255 * ratio * 2)
            return pygame.Color(255, green, 0)

    def draw_proportional_icon(self, window, icon, rect, alpha=255):
        img_w, img_h = icon.get_size()
        scale = min((rect.width - 10) / img_w, (rect.height - 10) / img_h)
        scaled_icon = pygame.transform.smoothscale(icon, (int(img_w * scale), int(img_h * scale)))
        if alpha < 255: scaled_icon.set_alpha(alpha)
        window.blit(scaled_icon, scaled_icon.get_rect(center=rect.center))

    def get_upgrade_action(self, reward_data):
        methods_map = {
            "add_weapons_1_speed": self.space_ship_parameters.add_weapons_1_speed,
            "add_weapons_1_damage": self.space_ship_parameters.add_weapons_1_damage,
            "reduce_weapons_1_reload": self.space_ship_parameters.reduce_weapons_1_reload,
            "add_weapons_2_speed": self.space_ship_parameters.add_weapons_2_speed,
            "add_weapons_2_max_speed": self.space_ship_parameters.add_weapons_2_max_speed,
            "add_weapons_2_damage": self.space_ship_parameters.add_weapons_2_damage,
            "reduce_weapons_2_reload": self.space_ship_parameters.reduce_weapons_2_reload,
            "add_weapons_2_time_alive": self.space_ship_parameters.add_weapons_2_time_alive,
            "add_weapons_2_steer_limit": self.space_ship_parameters.add_weapons_2_steer_limit,
            "reduce_max_switch_time": self.space_ship_parameters.reduce_max_switch_time,
            "add_max_shield_cooldown": self.space_ship_parameters.add_max_shield_cooldown,
            "add_shield_max_timer": self.space_ship_parameters.add_shield_max_timer,
            "reduce_linear_friction": self.space_ship_parameters.reduce_linear_friction,
            "add_braking_force": self.space_ship_parameters.add_braking_force,
            "add_max_boost_cooldown": self.space_ship_parameters.add_max_boost_cooldown,
            "add_hp_reg_speed": self.space_ship_parameters.add_hp_reg_speed,
            "add_max_hp": self.space_ship_parameters.add_max_hp,
            "add_max_speed": self.space_ship_parameters.add_max_speed,
            "add_boost_speed": self.space_ship_parameters.add_boost_speed,
            "add_thrust_power": self.space_ship_parameters.add_thrust_power            
        }

        for key, value in reward_data.items():
            if key in methods_map:
                action = lambda k=key, v=value: methods_map[k](v)
                raw_text = reward_data.get("text", "Bonus")
                formatted_text = raw_text.replace("{var}", str(value))
                return action, formatted_text
        
        return (lambda: None), "Błąd w pliku json 1203"

    def rewards_too_choose(self, rewards, dt):
        self.player_can_manevre = False
            
        # Jeśli level_manager.max_xp to np. 200, a przed chwilą był to 100,
        # to 100 staje się naszym nowym "zerem" dla paska.
        # Zakładając, że level_manager zwiększa max_xp o stałą wartość (np. 100):
        self.prev_max_xp =  self.level_manager.xp
        
        self.reward_shown_timer = 0
        self.is_closing_rewards = False
        
        self.reward_shown_timer = 0
        """Wywoływane przez Level Managera przy awansie"""
        # Przygotowujemy dane dla obu nagród
        act1, txt1 = self.get_upgrade_action(rewards.get("reward_1", {}))
        act2, txt2 = self.get_upgrade_action(rewards.get("reward_2", {}))
        
        self.active_rewards = {
            "1": {"action": act1, "text": txt1},
            "2": {"action": act2, "text": txt2}
        }
        self.show_reward_selection = True
        
        

    def _handle_reward_input(self):
        # Sprawdzamy, czy w ogóle mamy aktywne nagrody
        if not self.show_reward_selection or not self.active_rewards:
            return
        
        # SPRAWDZENIE: Czy minęła sekunda?
        if self.reward_shown_timer < self.reward_shown_timer_delay:
            return
        
        # Używamy .get(), aby VS Code przestał krzyczeć o potencjalne błędy kluczy
        reward1 = self.active_rewards.get("1")
        reward2 = self.active_rewards.get("2")

        if self.reward_1_choosed and reward1:
            self.show_reward_selection = False # Wyłączamy UI zanim wywołamy akcję
            reward1["action"]() 
            self._close_rewards()
            
        elif self.reward_2_choosed and reward2:
            self.show_reward_selection = False
            reward2["action"]()
            self._close_rewards()

    def _close_rewards(self):

        # Zamiast czyścić wszystko, odpalamy animację zanikania
        self.is_closing_rewards = True

    def _draw_reward_boxes(self, window):
        if self.reward_alpha <= 0:
            return

        # Przyciemnienie tła (dynamiczne alpha)
        overlay = pygame.Surface((self.cxx, self.cyy), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(self.reward_alpha * 0.7))) # Max ~180
        window.blit(overlay, (0, 0))

        box_w, box_h = 400, 150
        gap = 75
        start_x = (self.cxx - (2 * box_w + gap)) // 2
        y = (self.cyy - box_h) // 2

        keys_to_choose = ("O", "P")
        for i, key in enumerate(["1", "2"]):
            rect = pygame.Rect(start_x + i * (box_w + gap), y, box_w, box_h)
            
            # Główny box z alpha
            s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            pygame.draw.rect(s, (20, 30, 50, self.reward_alpha), (0, 0, box_w, box_h), border_radius=15)
            pygame.draw.rect(s, (0, 150, 255, self.reward_alpha), (0, 0, box_w, box_h), 3, border_radius=15)
            window.blit(s, rect)

            # Teksty z alpha
            reward_txt = self.active_rewards[key]["text"]
            txt_surf = self.font_big.render(reward_txt, True, (255, 255, 255))
            txt_surf.set_alpha(self.reward_alpha)
            window.blit(txt_surf, txt_surf.get_rect(center=(rect.centerx, rect.centery - 20)))

            key_surf = self.font.render(f"Naciśnij [{keys_to_choose[i]}] aby wybrać", True, (0, 200, 255))
            key_surf.set_alpha(self.reward_alpha)
            window.blit(key_surf, key_rect := key_surf.get_rect(center=(rect.centerx, rect.centery + 30)))

    def _actually_close_rewards(self):
        # To wywoła się, gdy alpha spadnie do 0
        self.show_reward_selection = False
        self.is_closing_rewards = False
        self.active_rewards = {}
        self.enemy_manager.can_start_new_level = True
        
        self.player_can_manevre = True


    def update(self, current_fps, dt):
        self.fps = current_fps
        self.pulse_time += dt
        
        # --- LOGIKA PASKA XP (OD ZERA NA KAŻDYM LEVELU) ---
        # Zakładamy, że level_manager ma informację o progu poprzedniego poziomu
        # Jeśli nie, możemy to emulować:
        current_xp_in_level = self.level_manager.xp - self.prev_max_xp
        max_xp_in_level = self.level_manager.max_xp - self.prev_max_xp
        
        # Płynne dążenie wyświetlanego XP do celu (interpolacja)
        target_xp_display = self.level_manager.xp
        self.displayed_xp += (target_xp_display - self.displayed_xp) * 0.1

        # --- ANIMACJA ALPHA OKNA NAGRÓD ---
        target_alpha = 0
        if self.show_reward_selection and not self.is_closing_rewards:
            target_alpha = 255
            self.reward_shown_timer += dt
        
        # Płynne przejście alpha (prędkość 10.0 steruje szybkością fade'u)
        alpha_speed = 10.0 * dt * 60 
        if self.reward_alpha < target_alpha:
            self.reward_alpha = min(target_alpha, self.reward_alpha + alpha_speed)
        elif self.reward_alpha > target_alpha:
            self.reward_alpha = max(target_alpha, self.reward_alpha - alpha_speed)
            if self.reward_alpha <= 0 and self.is_closing_rewards:
                self._actually_close_rewards() # Całkowite zamknięcie po wygaśnięciu
        self.fps = current_fps
        self.pulse_time += dt
        self.displayed_hp += (self.space_ship.hp - self.displayed_hp) * 0.1
        self.displayed_xp += (self.level_manager.xp - self.displayed_xp) * 0.05

        # Fizyka ramki broni
        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2
        self.target_x = start_x + self.battle.current_weapon * (self.slot_size + self.spacing)

        force = (self.target_x - self.frame_x) * self.spring_k
        self.frame_vel = (self.frame_vel + force) * self.friction
        self.frame_x += self.frame_vel
        if self.show_reward_selection:
            self.reward_shown_timer += dt
        self._handle_reward_input()

    def draw(self, window, camera):
        #0. celownik
        
        self._draw_enemy_lock_on(window, camera)
        
        # 1. Background Overlay
        overlay = pygame.Surface((self.cxx, 115), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 140), (0, 0, self.cxx, 115))
        window.blit(overlay, (0, 0))

        # 2. HP Section
        hp_x, hp_y, hp_w, hp_h = 20, 25, 220, 18
        
        # Obliczamy ratio na podstawie zmiennej max_hp ze statku
        # Dodajemy max(1, ...), aby uniknąć dzielenia przez zero w razie błędu
        current_max_hp = max(1, self.space_ship.max_hp)
        
        ratio = max(0, min(1, (self.space_ship.hp if self.space_ship.hp > 0 else 0)/ current_max_hp)) 
        ghost_ratio = max(0, min(1, self.displayed_hp / current_max_hp))
        
        # Rysowanie tła
        pygame.draw.rect(window, (40, 40, 50), (hp_x, hp_y, hp_w, hp_h), border_radius=4)
        
        # Pasek "ducha" (efekt otrzymywania obrażeń)
        if ghost_ratio > ratio:
            pygame.draw.rect(window, (150, 50, 50), (hp_x, hp_y, int(hp_w * ghost_ratio), hp_h), border_radius=4)
            
        # Pasek właściwy życia
        pygame.draw.rect(window, self.get_hp_color(ratio), (hp_x, hp_y, int(hp_w * ratio), hp_h), border_radius=4)
        
        # Ramka paska
        pygame.draw.rect(window, (200, 200, 200), (hp_x, hp_y, hp_w, hp_h), 2, border_radius=4)
        
        # Wyświetlanie tekstu HP: Aktualne / Max
        hp_text = f"HP: {int(self.space_ship.hp if self.space_ship.hp > 0 else 0)} / {int(current_max_hp)}"
        window.blit(self.font.render(hp_text, True, (255, 255, 255)), (hp_x, hp_y + 22))
        # 3. Weapons & Switching Bar
        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        weapon_specs = self.battle.weapons if self.battle.active_set == 1 else self.battle.weapons_2
        timers = self.battle.weapon_timers if self.battle.active_set == 1 else self.battle.weapon_timers_2
        is_switching = self.battle.switch_cooldown > 0
        
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2

        for i, path in enumerate(active_paths):
            x = start_x + i * (self.slot_size + self.spacing)
            rect = pygame.Rect(x, self.y_pos, self.slot_size, self.slot_size)
            is_selected = (i == self.battle.current_weapon)
            
            pygame.draw.rect(window, (30, 30, 50) if is_selected else (15, 15, 25), rect, border_radius=8)
            self.draw_proportional_icon(window, self.images[path], rect, alpha=255 if is_selected else 120)
            
            # Individual Cooldown
            p = min(timers[i] / weapon_specs[i][3], 1.0)
            if p < 1.0:
                h = int(self.slot_size * (1.0 - p))
                s = pygame.Surface((self.slot_size, h), pygame.SRCALPHA)
                s.fill((0, 0, 0, 180))
                window.blit(s, (x, self.y_pos))
            pygame.draw.rect(window, (100, 100, 120), rect, 1, border_radius=8)

        # Selection Glow
        theme_col = (255, 50, 50) if is_switching else (0, 220, 255)
        pygame.draw.rect(window, theme_col, (self.frame_x-3, self.y_pos-3, self.slot_size+6, self.slot_size+6), 2, border_radius=10)

        # Global Switching Bar (Pasek zmiany zestawów)
        if is_switching:
            sw_ratio = 1.0 - (self.battle.switch_cooldown / self.battle.max_switch_time)
            pygame.draw.rect(window, (40, 0, 0), (start_x, self.y_pos + self.slot_size + 8, total_w, 4))
            pygame.draw.rect(window, (255, 50, 50), (start_x, self.y_pos + self.slot_size + 8, int(total_w * sw_ratio), 4))

        # 4. XP & LEVEL Section
        xp_y = self.y_pos + self.slot_size + 22
        
        # OBLICZENIA RELATYWNE (od zera do max na danym poziomie)
        current_relative_xp = max(0, self.level_manager.xp - self.prev_max_xp)
        displayed_relative_xp = max(0, self.displayed_xp - self.prev_max_xp)
        level_capacity = max(1, self.level_manager.max_xp - self.prev_max_xp)

        xp_ratio = max(0, min(1, current_relative_xp / level_capacity))
        ghost_xp = max(0, min(1, displayed_relative_xp / level_capacity))
        
        #xp_ratio = max(0, min(1, self.level_manager.xp / self.level_manager.max_xp))
        #ghost_xp = max(0, min(1, self.displayed_xp / self.level_manager.max_xp))
        
        # Pasek XP
        pygame.draw.rect(window, (20, 20, 35), (start_x, xp_y, total_w, 6), border_radius=3)
        pygame.draw.rect(window, (0, 180, 255, 100), (start_x, xp_y, int(total_w * ghost_xp), 6), border_radius=3)
        pygame.draw.rect(window, (0, 120, 255), (start_x, xp_y, int(total_w * xp_ratio), 6), border_radius=3)
        
        # Tekst LEVEL pod paskiem
        lvl_text = f"LEVEL {self.level_manager.level}"
        xp_text = f"{int(self.level_manager.xp)} / {int(self.level_manager.max_xp)} XP"
        
        lvl_surf = self.font.render(lvl_text, True, (255, 215, 0)) # Złoty kolor dla poziomu
        xp_surf = self.font.render(xp_text, True, (150, 180, 255))
        
        window.blit(lvl_surf, (start_x, xp_y + 10))
        window.blit(xp_surf, (start_x + total_w - xp_surf.get_width(), xp_y + 10))
        # 5. Targeting Module
        self._draw_targeting_module(window, theme_col)

        # 6. Skills
        self._draw_skill_bar(window, start_x - 50, "Shield", 
                             self.battle.shield_timer / self.battle.shield_max_timer if self.battle.shield_active 
                             else 1.0 - (self.battle.shield_cooldown / self.battle.max_shield_cooldown), 
                             (255, 255, 255) if self.battle.shield_active else (0, 120, 255))
        
        ship = self.battle.player_main_class
        self._draw_skill_bar(window, start_x + total_w + 30, "Booster", 1.0 - (ship.boost_cooldown / ship.max_boost_cooldown), (255, 150, 0))

        self._draw_reward_boxes(window)

    def _draw_targeting_module(self, window, theme_color):
        if self.battle.active_set != 2:
            # Opcjonalnie: możemy tu zresetować namierzonego wroga, 
            # aby lasery nie "pamiętały" celu z rakiet
            self.battle.chosen_enemy = None
            return
        ui_x, ui_y = 25, self.cyy - 105
        panel_w, panel_h = 250, 80
        
        player_pos = pygame.math.Vector2(self.space_ship.player_pos)
        enemies = self.enemy_manager.enemies
        dists = [player_pos.distance_to(e.pos) for e in enemies] if enemies else []
        min_d = min(dists) if dists else 9999
        
        is_active = min_d < 3000
        self.battle.chosen_enemy = self.battle.enemy_choose(self.last_celowanie_mode if is_active else 0)

        # Panel Drawing
        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (10, 15, 25, 220), (0, 0, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(surf, (theme_color[0], theme_color[1], theme_color[2], 80), (0, 0, panel_w, panel_h), 2, border_radius=12)
        window.blit(surf, (ui_x, ui_y))

        # Signal Bars
        for i in range(5):
            bar_on = (is_active and self.battle.active_set == 2) and (min_d < (3500 - i * 600))
            pygame.draw.rect(window, theme_color if bar_on else (40, 45, 55), (ui_x + 15, ui_y + 55 - (i*9), 12, 6))

        # Text Info
        status_col = (0, 255, 180) if (is_active and self.battle.active_set == 2) else (250, 50, 50)
        window.blit(self.font.render("TARGETING COMPUTER", True, (140, 140, 150)), (ui_x + 40, ui_y + 12))
        
        status_surf = self.font_big.render("SYSTEM ONLINE" if (is_active and self.battle.active_set == 2) else "NO TARGETS", True, status_col)
        if not (is_active and self.battle.active_set == 2): status_surf.set_alpha(int(150 + 105 * math.sin(self.pulse_time * 12)))
        window.blit(status_surf, (ui_x + 40, ui_y + 28))

        if (is_active and self.battle.active_set == 2):
            mode_txt = "MODE: CLOSEST" if self.last_celowanie_mode == 1 else "MODE: FORWARD ANGLE"
            window.blit(self.font.render(mode_txt, True, (0, 180, 255)), (ui_x + 40, ui_y + 52))

        # Keys
        for i, (k, m) in enumerate([("R", 1), ("T", 2)]):
            col = (255, 255, 255) if self.last_celowanie_mode == m else (80, 80, 80)
            window.blit(self.font.render(k, True, col), ((ui_x + panel_w - 45 + i*20)+10, ui_y + 12))

    def _draw_skill_bar(self, window, x, label, ratio, color):
        bar_w, bar_h = 10, self.slot_size
        
        # 1. Rysowanie tła paska
        pygame.draw.rect(window, (30, 30, 40), (x, self.y_pos, bar_w, bar_h), border_radius=2)
        
        # 2. Rysowanie wypełnienia (od dołu do góry)
        f_h = int(bar_h * max(0, min(1, ratio)))
        pygame.draw.rect(window, color, (x, self.y_pos + (bar_h - f_h), bar_w, f_h), border_radius=2)
        
        # 3. Renderowanie i centrowanie etykiety
        text_surf = self.font.render(label, True, (130, 130, 140))
        
        # Obliczamy środek paska (x + połowa bar_w) 
        # i odejmujemy połowę szerokości tekstu
        text_x = x + (bar_w // 2) - (text_surf.get_width() // 2)
        text_y = self.y_pos + bar_h + 5
        
        window.blit(text_surf, (text_x, text_y))
        
    # W pliku ui.py podmień metodę _draw_enemy_lock_on:
    def _draw_enemy_lock_on(self, window, camera):
        if self.battle.active_set != 2:
            return
        
        target = getattr(self.battle, 'chosen_enemy', None)
        if not target or getattr(target, 'hp', 0) <= 0:
            return

        target_screen_pos = camera.apply(target.pos)
        tx, ty = target_screen_pos[0], target_screen_pos[1]
        color = (255, 50, 50) 

        is_off_screen = (tx < 0 or tx > self.cxx or ty < 115 or ty > self.cyy)

        if not is_off_screen:
            # --- 1. CELOWNIK NA EKRANIE (bez zmian, dla spójności) ---
            size = 50 + 5 * math.sin(self.pulse_time * 12)
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (int(tx), int(ty))
            thickness = 2
            length = int(size * 0.25)
            pygame.draw.lines(window, color, False, [(rect.left, rect.top + length), (rect.left, rect.top), (rect.left + length, rect.top)], thickness)
            pygame.draw.lines(window, color, False, [(rect.right - length, rect.top), (rect.right, rect.top), (rect.right, rect.top + length)], thickness)
            pygame.draw.lines(window, color, False, [(rect.left, rect.bottom - length), (rect.left, rect.bottom), (rect.left + length, rect.bottom)], thickness)
            pygame.draw.lines(window, color, False, [(rect.right - length, rect.bottom), (rect.right, rect.bottom), (rect.right, rect.bottom - length)], thickness)
            pygame.draw.circle(window, color, rect.center, 3)
            dist = self.space_ship.player_pos.distance_to(target.pos)
            dist_txt = self.font.render(f"{int(dist)}m", True, color)
            window.blit(dist_txt, (rect.centerx - dist_txt.get_width()//2, rect.bottom + 5))

        else:
            # --- 2. ŁADNIEJSZA STRZAŁKA POZA EKRANEM ---
            margin = 40
            ui_offset_y = 115
            
            # Animacja pulsowania (odległość od krawędzi)
            bounce = math.sin(self.pulse_time * 10) * 5
            
            # Wyznaczanie pozycji na krawędzi
            edge_x = max(margin, min(self.cxx - margin, tx))
            edge_y = max(margin + ui_offset_y, min(self.cyy - margin, ty))
            
            arrow_pos = pygame.math.Vector2(edge_x, edge_y)
            
            # Obliczanie kierunku do celu
            direction = pygame.math.Vector2(tx, ty) - arrow_pos
            if direction.length() > 0:
                angle = math.degrees(math.atan2(direction.y, direction.x))
                # Przesunięcie o bounce w stronę celu
                arrow_pos += direction.normalize() * bounce
            else:
                angle = 0

            # --- EFEKT POŚWIATY (Glow) ---
            glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            glow_alpha = int(100 + 50 * math.sin(self.pulse_time * 10))
            pygame.draw.circle(glow_surf, (color[0], color[1], color[2], glow_alpha // 3), (30, 30), 25)
            pygame.draw.circle(glow_surf, (color[0], color[1], color[2], glow_alpha // 6), (30, 30), 15)
            window.blit(glow_surf, glow_surf.get_rect(center=(int(arrow_pos.x), int(arrow_pos.y))))

            # --- RYSOWANIE STRZAŁKI (Trójkąt równoramienny, ostrzejszy) ---
            p1 = arrow_pos + pygame.math.Vector2(18, 0).rotate(angle)      # Czubek (dłuższy)
            p2 = arrow_pos + pygame.math.Vector2(-12, -8).rotate(angle)    # Tył góra
            p3 = arrow_pos + pygame.math.Vector2(-12, 8).rotate(angle)     # Tył dół
            
            # Obrys dla lepszej widoczności na jasnym tle
            pygame.draw.polygon(window, (20, 20, 20), [p1, p2, p3], 4) 
            pygame.draw.polygon(window, color, [p1, p2, p3])
            
            # --- DYSTANS (Z tłem pod tekstem) ---
            dist = self.space_ship.player_pos.distance_to(target.pos)
            dist_txt = self.font.render(f"{int(dist)}m", True, (255, 255, 255))
            
            # Pozycja tekstu zawsze lekko "do wewnątrz" ekranu od strzałki
            text_off = pygame.math.Vector2(-45, 0).rotate(angle)
            # Zabezpieczenie, żeby tekst nie uciekł za ekran
            tx_final = max(50, min(self.cxx - 50, arrow_pos.x + text_off.x))
            ty_final = max(ui_offset_y + 20, min(self.cyy - 20, arrow_pos.y + text_off.y))
            
            # Mały cień pod tekstem
            dist_rect = dist_txt.get_rect(center=(tx_final, ty_final))
            bg_rect = dist_rect.inflate(8, 4)
            pygame.draw.rect(window, (0, 0, 0, 150), bg_rect, border_radius=4)
            window.blit(dist_txt, dist_rect)