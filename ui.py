import pygame
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_ship import SpaceShip
    from space_ship import Battle
    from event import Event

class GameController:
    def __init__(self, battle: "Battle", event_obj: "Event", player: "SpaceShip", cxx: int, cyy: int, loaded_images: dict, clock: pygame.time.Clock):
        self.ui = UI(event_obj, cxx, cyy, loaded_images, battle, player)
        self.input_handler = InputHandler(event_obj, player, battle, self.ui)
        self.clock = clock

    def update(self, dt: float):
        self.input_handler.update()
        self.ui.update(self.clock.get_fps(), dt)

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
    def __init__(self, event_obj: "Event", screen_width: int, screen_height: int, images: dict, battle: "Battle", space_ship: "SpaceShip"):
        self.event_obj = event_obj
        self.images = images
        self.battle = battle
        self.cxx = screen_width
        self.cyy = screen_height
        self.space_ship = space_ship
        
        self.displayed_hp = space_ship.hp
        self.max_hp = 100
        self.pulse_time = 0 
        
        try:
            self.font = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 16)
            self.font_big = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 20)
        except:
            self.font = pygame.font.SysFont("Arial", 16, bold=True)
            self.font_big = pygame.font.SysFont("Arial", 20, bold=True)

        self.laser_paths = ["images/Lasers/laserBlue12.png", "images/Lasers/laserBlue13.png", "images/Lasers/laserBlue14.png", "images/Lasers/laserBlue15.png", "images/Lasers/laserBlue16.png"]
        self.missile_paths = [f"images/Missiles/spaceMissiles_{p}.png" for p in ["001", "004", "007", "010", "013", "016", "019", "022", "025"]]

        self.fps = 0
        self.slot_size = 55
        self.spacing = 8
        self.y_pos = 25
        
        # --- ZMODYFIKOWANA FIZYKA (Mniej sprężyny, więcej sztywności) ---
        self.frame_x = screen_width // 2
        self.frame_vel = 0
        self.target_x = 0
        self.spring_k = 0.5    # Bardzo silne przyciąganie
        self.friction = 0.4    # Bardzo wysokie tłumienie (szybko zabija pęd)

    def get_hp_color(self, ratio: float) -> pygame.Color:
        ratio = max(0, min(1, ratio))
        if ratio > 0.5:
            return pygame.Color(int(255 * (1 - ratio) * 2), 255, 0)
        return pygame.Color(255, int(255 * ratio * 2), 0)

    def draw_proportional_icon(self, window: pygame.Surface, icon: pygame.Surface, rect: pygame.Rect, alpha=255):
        img_w, img_h = icon.get_size()
        padding = 10
        max_dim = rect.width - padding
        scale = min(max_dim / img_w, max_dim / img_h)
        scaled_icon = pygame.transform.smoothscale(icon, (int(img_w * scale), int(img_h * scale)))
        if alpha < 255:
            scaled_icon.set_alpha(alpha)
        window.blit(scaled_icon, scaled_icon.get_rect(center=rect.center))

    def update(self, current_fps: float, dt: float):
        self.fps = current_fps
        self.pulse_time += dt
        
        if self.displayed_hp > self.space_ship.hp:
            self.displayed_hp -= (self.displayed_hp - self.space_ship.hp) * 0.1
        else:
            self.displayed_hp = self.space_ship.hp

        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2
        
        self.target_x = start_x + self.battle.current_weapon * (self.slot_size + self.spacing)

        # Fizyka - im mniejszy friction i większy k, tym ruch jest sztywniejszy
        force = (self.target_x - self.frame_x) * self.spring_k
        self.frame_vel += force
        self.frame_vel *= self.friction
        self.frame_x += self.frame_vel

        # Natychmiastowe wyrównanie przy małym błędzie
        if abs(self.frame_x - self.target_x) < 0.5:
            self.frame_x = self.target_x
            self.frame_vel = 0

    def draw(self, window: pygame.Surface):
        overlay = pygame.Surface((self.cxx, 110), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 100), (0, 0, self.cxx, 110))
        window.blit(overlay, (0, 0))

        fps_text = self.font.render(f"FPS: {int(self.fps)}", True, (0, 255, 100))
        window.blit(fps_text, (self.cxx - fps_text.get_width() - 20 , 20))

        hp_x, hp_y, hp_w, hp_h = 20, 25, 220, 18
        actual_ratio = max(0, self.space_ship.hp / self.max_hp)
        ghost_ratio = max(0, self.displayed_hp / self.max_hp)
        hp_col = self.get_hp_color(actual_ratio)

        if actual_ratio < 0.25:
            pulse = int(170 + 85 * math.sin(self.pulse_time * 15))
            hp_col = pygame.Color(pulse, 20, 20)

        pygame.draw.rect(window, (30, 30, 40), (hp_x, hp_y, hp_w, hp_h), border_radius=6)
        if ghost_ratio > actual_ratio:
            pygame.draw.rect(window, (150, 50, 50), (hp_x, hp_y, int(hp_w * ghost_ratio), hp_h), border_radius=6)
        if actual_ratio > 0:
            pygame.draw.rect(window, hp_col, (hp_x, hp_y, int(hp_w * actual_ratio), hp_h), border_radius=6)
        pygame.draw.rect(window, (200, 200, 200), (hp_x, hp_y, hp_w, hp_h), 2, border_radius=6)
        
        hp_label = self.font.render(f"HEALTH: {int(actual_ratio*100)}%", True, (255, 255, 255))
        window.blit(hp_label, (hp_x, hp_y + hp_h + 5))

        active_paths = self.laser_paths if self.battle.active_set == 1 else self.missile_paths
        weapon_specs = self.battle.weapons if self.battle.active_set == 1 else self.battle.weapons_2
        timers = self.battle.weapon_timers if self.battle.active_set == 1 else self.battle.weapon_timers_2
        is_switching = self.battle.switch_cooldown > 0

        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2

        for i, path in enumerate(active_paths):
            x = start_x + i * (self.slot_size + self.spacing)
            is_selected = (i == self.battle.current_weapon)
            rect = pygame.Rect(x, self.y_pos, self.slot_size, self.slot_size)
            
            bg_col = (60, 60, 100, 220) if is_selected else (40, 40, 60, 200)
            slot_bg = pygame.Surface((self.slot_size, self.slot_size), pygame.SRCALPHA)
            pygame.draw.rect(slot_bg, bg_col, (0, 0, self.slot_size, self.slot_size), border_radius=8)
            window.blit(slot_bg, (x, self.y_pos))
            
            self.draw_proportional_icon(window, self.images[path], rect, alpha=255 if is_selected else 160)

            progress = min(timers[i] / weapon_specs[i][3], 1.0)
            if progress < 1.0:
                overlay_h = int(self.slot_size * (1.0 - progress))
                re_overlay = pygame.Surface((self.slot_size, overlay_h), pygame.SRCALPHA)
                re_overlay.fill((0, 0, 0, 200))
                window.blit(re_overlay, (x, self.y_pos))
            pygame.draw.rect(window, (100, 100, 120), rect, 1, border_radius=8)

        glow_col = (255, 50, 50) if is_switching else (0, 220, 255)
        for j in range(3):
            pygame.draw.rect(window, glow_col, (self.frame_x-2-j, self.y_pos-2-j, self.slot_size+4+j*2, self.slot_size+4+j*2), 1, border_radius=10)

        mode_name = ">> LASER SYSTEM ACTIVE <<" if self.battle.active_set == 1 else ">> MISSILE RACKS LOADED <<"
        if is_switching: 
            mode_name = "!! RECALIBRATING SYSTEMS !!"
            sw_ratio = 1.0 - (self.battle.switch_cooldown / self.battle.max_switch_time)
            pygame.draw.rect(window, (50, 0, 0), (start_x, self.y_pos + self.slot_size + 5, total_w, 4))
            pygame.draw.rect(window, (0, 255, 255), (start_x, self.y_pos + self.slot_size + 5, int(total_w * sw_ratio), 4))

        mode_txt = self.font_big.render(mode_name, True, glow_col)
        txt_alpha = int(155 + 100 * math.sin(self.pulse_time * 10))
        mode_txt.set_alpha(txt_alpha)
        window.blit(mode_txt, (self.cxx // 2 - mode_txt.get_width() // 2, self.y_pos + self.slot_size + 15))

        if self.battle.shield_active:
            s_ratio = self.battle.shield_timer / self.battle.shield_max_timer
            s_col = (255, 255, 255)
        else:
            s_ratio = 1.0 - (self.battle.shield_cooldown / self.battle.max_shield_cooldown)
            s_col = (0, 150, 255)
        self._draw_skill_bar(window, start_x - 50, "SHIELD", s_ratio, s_col)
        
        ship = self.battle.player_main_class
        b_ratio = 1.0 - (ship.boost_cooldown / ship.max_boost_cooldown)
        b_col = (255, 150, 0) if ship.is_boost_ready else (100, 50, 0)
        self._draw_skill_bar(window, start_x + total_w + 30, "BOOST", b_ratio, b_col)

    def _draw_skill_bar(self, window, x, label, ratio, color):
        bar_w, bar_h = 12, self.slot_size
        pygame.draw.rect(window, (20, 20, 30), (x, self.y_pos, bar_w, bar_h), border_radius=2)
        fill_h = int(bar_h * max(0, min(1, ratio)))
        pygame.draw.rect(window, color, (x, self.y_pos + (bar_h - fill_h), bar_w, fill_h), border_radius=2)
        txt = self.font.render(label, True, (150, 150, 150))
        tx = x + (bar_w // 2) - (txt.get_width() // 2)
        window.blit(txt, (tx, self.y_pos + bar_h + 5))