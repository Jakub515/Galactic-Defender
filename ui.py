import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_ship import SpaceShip
    from space_ship import Battle
    from functions import Event

class GameController:
    def __init__(self, battle: "Battle", event_obj: "Event", player: "SpaceShip", cxx: int, cyy: int, loaded_images: dict, clock: pygame.time.Clock):
        self.ui = UI(event_obj, cxx, cyy, loaded_images, battle)
        self.input_handler = InputHandler(event_obj, player, battle, self.ui)
        self.clock = clock

    def update(self, dt: float):
        self.input_handler.update()
        self.ui.update(self.clock.get_fps())

    def draw(self, window: pygame.Surface):
        self.ui.draw(window)

class InputHandler:
    def __init__(self, event_obj: "Event", player_obj: "SpaceShip", player_shoot: "Battle", ui_obj: "UI"):
        self.event_obj = event_obj
        self.player_obj = player_obj
        self.ctrl_pressed_last_frame = False
        self.player_shoot = player_shoot
        self.ui_obj = ui_obj
    
    def update(self):
        self.player_obj.thrust(self.event_obj.key_up, boost=self.event_obj.backquote)
        if self.event_obj.key_left: self.player_obj.rotate(1)
        elif self.event_obj.key_right: self.player_obj.rotate(-1)
        else: self.player_obj.rotate(0)
        self.player_obj.brake(self.event_obj.key_down)

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
    def __init__(self, event_obj: "Event", screen_width: int, screen_height: int, images: dict, battle: "Battle"):
        self.event_obj = event_obj
        self.images = images
        self.battle = battle
        self.cxx = screen_width
        self.cyy = screen_height
        
        try:
            self.font = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 16)
        except:
            self.font = pygame.font.SysFont("Arial", 16, bold=True)

        self.laser_paths = ["images/Lasers/laserBlue12.png", "images/Lasers/laserBlue13.png", "images/Lasers/laserBlue14.png", "images/Lasers/laserBlue15.png", "images/Lasers/laserBlue16.png"]
        self.missile_paths = [f"images/Missiles/spaceMissiles_{p}.png" for p in ["001", "004", "007", "010", "013", "016", "019", "022", "025"]]

        self.fps = 0
        self.slot_size = 55
        self.spacing = 8
        self.y_pos = 25
        self.frame_x = 0
        self.target_x = 0
        self.lerp_speed = 0.15

    def draw_proportional_icon(self, window: pygame.Surface, icon: pygame.Surface, rect: pygame.Rect):
        img_w, img_h = icon.get_size()
        padding = 10
        max_dim = self.slot_size - padding
        scale = min(max_dim / img_w, max_dim / img_h)
        scaled_icon = pygame.transform.smoothscale(icon, (int(img_w * scale), int(img_h * scale)))
        window.blit(scaled_icon, scaled_icon.get_rect(center=rect.center))

    def update(self, current_fps: float):
        self.fps = current_fps
        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        current_idx = self.battle.current_weapon
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2
        self.target_x = start_x + current_idx * (self.slot_size + self.spacing)
        
        if abs(self.target_x - self.frame_x) > 400: self.frame_x = self.target_x
        self.frame_x += (self.target_x - self.frame_x) * self.lerp_speed

    def draw(self, window: pygame.Surface):
        # 1. FPS
        fps_text = self.font.render(f"FPS: {int(self.fps)}", True, (0, 255, 100))
        window.blit(fps_text, (self.cxx - fps_text.get_width() - 20, 20))

        # 2. Dane o broniach
        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        weapon_specs = self.battle.weapons if self.battle.active_set == 1 else self.battle.weapons_2
        timers = self.battle.weapon_timers if self.battle.active_set == 1 else self.battle.weapon_timers_2
        
        # Sprawdzanie czy trwa przeładowanie pocisku lub blokada zestawu
        is_bullet_reloading = any(timers[i] < weapon_specs[i][3] for i in range(len(weapon_specs)))
        is_switching = self.battle.switch_cooldown > 0
        is_busy = is_bullet_reloading or is_switching

        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2

        # Tło całego paska (opcjonalne, dla lepszej czytelności)
        # pygame.draw.rect(window, (10, 10, 20, 100), (start_x - 10, self.y_pos - 10, total_w + 20, self.slot_size + 20), border_radius=10)

        for i, path in enumerate(active_paths):
            x = start_x + i * (self.slot_size + self.spacing)
            slot_rect = pygame.Rect(x, self.y_pos, self.slot_size, self.slot_size)
            
            # Tło slotu
            s = pygame.Surface((self.slot_size, self.slot_size), pygame.SRCALPHA)
            pygame.draw.rect(s, (20, 20, 30, 200), (0, 0, self.slot_size, self.slot_size), border_radius=5)
            window.blit(s, (x, self.y_pos))
            pygame.draw.rect(window, (80, 80, 100), slot_rect, 1, border_radius=5)
            
            # Ikona
            self.draw_proportional_icon(window, self.images[path], slot_rect)

            # --- INDYWIDUALNY RELOAD POCISKU ---
            progress = min(timers[i] / weapon_specs[i][3], 1.0)
            if progress < 1.0:
                reload_surf = pygame.Surface((self.slot_size, self.slot_size), pygame.SRCALPHA)
                h = int(self.slot_size * (1.0 - progress))
                pygame.draw.rect(reload_surf, (0, 0, 0, 150), (0, 0, self.slot_size, h))
                window.blit(reload_surf, (x, self.y_pos))

            # Numer klawisza
            key_label = self.font.render(str(i + 1), True, (200, 200, 200))
            window.blit(key_label, (x + 5, self.y_pos + 2))

        # --- NOWE: ANIMACJA ZMIANY ZESTAWU (Global Cooldown) ---
        if is_switching:
            switch_progress = 1.0 - (self.battle.switch_cooldown / self.battle.max_switch_time)
            # Czerwony pasek postępu nad wszystkimi slotami
            bar_width = int(total_w * switch_progress)
            pygame.draw.rect(window, (255, 0, 50), (start_x, self.y_pos + self.slot_size + 2, total_w, 4), border_radius=2)
            pygame.draw.rect(window, (0, 255, 255), (start_x, self.y_pos + self.slot_size + 2, bar_width, 4), border_radius=2)

        # 3. Ramka wyboru
        glow_color = (255, 50, 50) if is_busy else (0, 200, 255)
        glow_rect = pygame.Rect(self.frame_x - 2, self.y_pos - 2, self.slot_size + 4, self.slot_size + 4)
        pygame.draw.rect(window, glow_color, glow_rect, 3, border_radius=6)
        
        # 4. Nazwa trybu i status
        mode_name = "SYSTEM LASEROWY" if self.battle.active_set == 1 else "WYRZUTNIA RAKIET"
        if is_switching: mode_name = "REKALIBRACJA SYSTEMÓW..."
        
        mode_txt = self.font.render(mode_name, True, glow_color)
        window.blit(mode_txt, (self.cxx // 2 - mode_txt.get_width() // 2, self.y_pos + self.slot_size + 12))

# Reszta klas (GameController, InputHandler) bez zmian...