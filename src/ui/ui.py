import pygame
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jednostki.space_ship import Battle, Parameters, SpaceShip
    from jednostki.enemy_ship.enemy_manager import EnemyManager
    from core.event import Event
    from core.level_manager import LevelManager
    from utils.collisions import Collision

# --- KOMPONENTY POMOCNICZE (LOGIKA I RYSOWANIE) ---

class StatsComponent:
    """Obsługuje Pasek HP oraz Pasek XP."""
    def __init__(self, font):
        self.font = font
        self.displayed_hp = 0
        self.displayed_xp = 0
        self.prev_max_xp = 0

    def update(self, actual_hp, actual_xp, dt):
        self.displayed_hp += (actual_hp - self.displayed_hp) * 0.1
        self.displayed_xp += (actual_xp - self.displayed_xp) * 0.05

    def get_hp_color(self, ratio):
        ratio = max(0.0, min(1.0, ratio))
        if ratio > 0.5:
            return pygame.Color(int(255 * (1 - ratio) * 2), 255, 0)
        return pygame.Color(255, int(255 * ratio * 2), 0)

    def draw(self, window, ship, level_manager, start_x, total_w):
        # HP Bar
        hp_x, hp_y, hp_w, hp_h = 20, 25, 220, 18
        max_hp = max(1, ship.max_hp)
        ratio = max(0, min(1, ship.hp / max_hp))
        ghost_ratio = max(0, min(1, self.displayed_hp / max_hp))

        pygame.draw.rect(window, (40, 40, 50), (hp_x, hp_y, hp_w, hp_h), border_radius=4)
        if ghost_ratio > ratio:
            pygame.draw.rect(window, (150, 50, 50), (hp_x, hp_y, int(hp_w * ghost_ratio), hp_h), border_radius=4)
        pygame.draw.rect(window, self.get_hp_color(ratio), (hp_x, hp_y, int(hp_w * ratio), hp_h), border_radius=4)
        pygame.draw.rect(window, (200, 200, 200), (hp_x, hp_y, hp_w, hp_h), 2, border_radius=4)
        
        hp_txt = self.font.render(f"HP: {int(max(0, ship.hp))} / {int(max_hp)}", True, (255, 255, 255))
        window.blit(hp_txt, (hp_x, hp_y + 22))

        # XP Bar
        xp_y = 25 + 55 + 22
        curr_rel_xp = max(0, level_manager.xp - self.prev_max_xp)
        max_rel_xp = max(1, level_manager.max_xp - self.prev_max_xp)
        ghost_rel_xp = max(0, self.displayed_xp - self.prev_max_xp)
        
        xp_ratio = max(0, min(1, curr_rel_xp / max_rel_xp))
        ghost_xp_ratio = max(0, min(1, ghost_rel_xp / max_rel_xp))

        pygame.draw.rect(window, (20, 20, 35), (start_x, xp_y, total_w, 6), border_radius=3)
        pygame.draw.rect(window, (0, 180, 255, 100), (start_x, xp_y, int(total_w * ghost_xp_ratio), 6), border_radius=3)
        pygame.draw.rect(window, (0, 120, 255), (start_x, xp_y, int(total_w * xp_ratio), 6), border_radius=3)

        lvl_surf = self.font.render(f"LEVEL {level_manager.level}", True, (255, 215, 0))
        xp_surf = self.font.render(f"{int(level_manager.xp)} / {int(level_manager.max_xp)} XP", True, (150, 180, 255))
        window.blit(lvl_surf, (start_x, xp_y + 10))
        window.blit(xp_surf, (start_x + total_w - xp_surf.get_width(), xp_y + 10))


class WeaponComponent:
    """Obsługuje sloty broni, przełączanie i skille (Shield/Boost)."""
    def __init__(self, images, laser_paths, missile_paths, font):
        self.images = images
        self.paths = {1: laser_paths, 2: missile_paths}
        self.font = font
        self.frame_x = 0
        self.frame_vel = 0
        self.slot_size = 55
        self.spacing = 8

    def update(self, battle, screen_width, dt):
        active_paths = self.paths[battle.active_set]
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (screen_width - total_w) // 2
        target_x = start_x + battle.current_weapon * (self.slot_size + self.spacing)
        
        force = (target_x - self.frame_x) * 0.5
        self.frame_vel = (self.frame_vel + force) * 0.4
        self.frame_x += self.frame_vel

    def draw(self, window, battle, screen_width, y_pos):
        active_paths = self.paths[battle.active_set]
        weapon_specs = battle.weapons if battle.active_set == 1 else battle.weapons_2
        timers = battle.weapon_timers if battle.active_set == 1 else battle.weapon_timers_2
        
        total_w = len(active_paths) * (self.slot_size + self.spacing) - self.spacing
        start_x = (screen_width - total_w) // 2

        for i, path in enumerate(active_paths):
            x = start_x + i * (self.slot_size + self.spacing)
            rect = pygame.Rect(x, y_pos, self.slot_size, self.slot_size)
            is_sel = (i == battle.current_weapon)
            
            pygame.draw.rect(window, (30, 30, 50) if is_sel else (15, 15, 25), rect, border_radius=8)
            
            # Ikona
            img = self.images[path]
            scale = min((rect.width - 10) / img.get_width(), (rect.height - 10) / img.get_height())
            s_img = pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            if not is_sel: s_img.set_alpha(120)
            window.blit(s_img, s_img.get_rect(center=rect.center))

            # Cooldown
            p = min(timers[i] / weapon_specs[i][3], 1.0)
            if p < 1.0:
                h = int(self.slot_size * (1.0 - p))
                s = pygame.Surface((self.slot_size, h), pygame.SRCALPHA)
                s.fill((0, 0, 0, 180))
                window.blit(s, (x, y_pos))
            pygame.draw.rect(window, (100, 100, 120), rect, 1, border_radius=8)

        # Ramka wyboru
        theme_col = (255, 50, 50) if battle.switch_cooldown > 0 else (0, 220, 255)
        pygame.draw.rect(window, theme_col, (self.frame_x-3, y_pos-3, self.slot_size+6, self.slot_size+6), 2, border_radius=10)
        
        # Pasek zmiany zestawu
        if battle.switch_cooldown > 0:
            sw_ratio = 1.0 - (battle.switch_cooldown / battle.max_switch_time)
            pygame.draw.rect(window, (40, 0, 0), (start_x, y_pos + self.slot_size + 8, total_w, 4))
            pygame.draw.rect(window, (255, 50, 50), (start_x, y_pos + self.slot_size + 8, int(total_w * sw_ratio), 4))

        return start_x, total_w

    def draw_skill_bar(self, window, x, y, label, ratio, color):
        bar_w, bar_h = 10, self.slot_size
        pygame.draw.rect(window, (30, 30, 40), (x, y, bar_w, bar_h), border_radius=2)
        f_h = int(bar_h * max(0, min(1, ratio)))
        pygame.draw.rect(window, color, (x, y + (bar_h - f_h), bar_w, f_h), border_radius=2)
        txt = self.font.render(label, True, (130, 130, 140))
        window.blit(txt, (x + (bar_w//2) - (txt.get_width()//2), y + bar_h + 5))


class TargetingComponent:
    """Logika namierzania i rysowania celownika/strzałek."""
    def __init__(self, font, font_big, screen_w, screen_h):
        self.font = font
        self.font_big = font_big
        self.cxx, self.cyy = screen_w, screen_h

    def update_logic(self, battle, enemy_manager, ship, last_mode):
        if battle.active_set != 2:
            battle.chosen_enemy = None
            return False, 9999
        
        enemies = enemy_manager.enemies
        dists = [ship.player_pos.distance_to(e.pos) for e in enemies] if enemies else []
        min_d = min(dists) if dists else 9999
        is_active = min_d < 3000
        battle.chosen_enemy = battle.enemy_choose(last_mode if is_active else 0)
        return is_active, min_d

    def draw_module(self, window, is_active, min_d, last_mode, pulse_time, theme_color):
        ui_x, ui_y = 25, self.cyy - 105
        panel_w, panel_h = 250, 80
        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (10, 15, 25, 220), (0, 0, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(surf, (*theme_color[:3], 80), (0, 0, panel_w, panel_h), 2, border_radius=12)
        window.blit(surf, (ui_x, ui_y))

        for i in range(5):
            bar_on = is_active and (min_d < (3500 - i * 600))
            pygame.draw.rect(window, theme_color if bar_on else (40, 45, 55), (ui_x + 15, ui_y + 55 - (i*9), 12, 6))

        status_col = (0, 255, 180) if is_active else (250, 50, 50)
        window.blit(self.font.render("TARGETING COMPUTER", True, (140, 140, 150)), (ui_x + 40, ui_y + 12))
        status_surf = self.font_big.render("SYSTEM ONLINE" if is_active else "NO TARGETS", True, status_col)
        if not is_active: status_surf.set_alpha(int(150 + 105 * math.sin(pulse_time * 12)))
        window.blit(status_surf, (ui_x + 40, ui_y + 28))

        if is_active:
            mode_txt = "MODE: CLOSEST" if last_mode == 1 else "MODE: FORWARD ANGLE"
            window.blit(self.font.render(mode_txt, True, (0, 180, 255)), (ui_x + 40, ui_y + 52))

        for i, (k, m) in enumerate([("R", 1), ("T", 2)]):
            col = (255, 255, 255) if last_mode == m else (80, 80, 80)
            window.blit(self.font.render(k, True, col), (ui_x + panel_w - 35 + i*20, ui_y + 12))

    def draw_lock_on(self, window, camera, battle, ship, pulse_time):
        target = getattr(battle, 'chosen_enemy', None)
        if not target or getattr(target, 'hp', 0) <= 0: return

        tx, ty = camera.apply(target.pos)
        color = (255, 50, 50)
        is_off = (tx < 0 or tx > self.cxx or ty < 115 or ty > self.cyy)

        if not is_off:
            size = 50 + 5 * math.sin(pulse_time * 12)
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (int(tx), int(ty))
            length = int(size * 0.25)
            for start, end1, end2 in [(rect.topleft, (0, length), (length, 0)), (rect.topright, (0, length), (-length, 0)),
                                       (rect.bottomleft, (0, -length), (length, 0)), (rect.bottomright, (0, -length), (-length, 0))]:
                pygame.draw.lines(window, color, False, [(start[0], start[1]+end1[1]), start, (start[0]+end2[0], start[1])], 2)
            pygame.draw.circle(window, color, rect.center, 3)
            dist_txt = self.font.render(f"{int(ship.player_pos.distance_to(target.pos))}m", True, color)
            window.blit(dist_txt, (rect.centerx - dist_txt.get_width()//2, rect.bottom + 5))
        else:
            margin, ui_off = 40, 115
            bounce = math.sin(pulse_time * 10) * 5
            edge_x = max(margin, min(self.cxx - margin, tx))
            edge_y = max(margin + ui_off, min(self.cyy - margin, ty))
            
            arrow_pos = pygame.math.Vector2(edge_x, edge_y)
            direction = pygame.math.Vector2(tx, ty) - arrow_pos
            if direction.length() > 0:
                angle = math.degrees(math.atan2(direction.y, direction.x))
                arrow_pos += direction.normalize() * bounce
            else: angle = 0

            p1 = arrow_pos + pygame.math.Vector2(18, 0).rotate(angle)
            p2 = arrow_pos + pygame.math.Vector2(-12, -8).rotate(angle)
            p3 = arrow_pos + pygame.math.Vector2(-12, 8).rotate(angle)
            pygame.draw.polygon(window, (20, 20, 20), [p1, p2, p3], 4)
            pygame.draw.polygon(window, color, [p1, p2, p3])


class RewardComponent:
    """Zarządza oknem wyboru ulepszeń."""
    def __init__(self, font, font_big, screen_w, screen_h):
        self.font = font
        self.font_big = font_big
        self.cxx, self.cyy = screen_w, screen_h
        self.alpha = 0
        self.is_closing = False

    def update(self, active, dt):
        target = 255 if active and not self.is_closing else 0
        speed = 10.0 * dt * 60
        if self.alpha < target: self.alpha = min(target, self.alpha + speed)
        elif self.alpha > target: self.alpha = max(0, self.alpha - speed)

    def draw(self, window, active_rewards):
        if self.alpha <= 0: return
        overlay = pygame.Surface((self.cxx, self.cyy), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(self.alpha * 0.7)))
        window.blit(overlay, (0, 0))

        box_w, box_h, gap = 400, 150, 75
        start_x = (self.cxx - (2 * box_w + gap)) // 2
        y = (self.cyy - box_h) // 2

        for i, key in enumerate(["1", "2"]):
            rect = pygame.Rect(start_x + i * (box_w + gap), y, box_w, box_h)
            s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            pygame.draw.rect(s, (20, 30, 50, self.alpha), (0, 0, box_w, box_h), border_radius=15)
            pygame.draw.rect(s, (0, 150, 255, self.alpha), (0, 0, box_w, box_h), 3, border_radius=15)
            window.blit(s, rect)

            txt = self.font_big.render(active_rewards[key]["text"], True, (255, 255, 255))
            txt.set_alpha(self.alpha)
            window.blit(txt, txt.get_rect(center=(rect.centerx, rect.centery - 20)))
            
            hint = self.font.render(f"Naciśnij [{'O' if i==0 else 'P'}] aby wybrać", True, (0, 200, 255))
            hint.set_alpha(self.alpha)
            window.blit(hint, hint.get_rect(center=(rect.centerx, rect.centery + 30)))
import pygame
import math
import random

class GameOverComponent:
    """Ultra-płynny ekran porażki z efektami post-procesingu i inteligentnym losowaniem tekstów."""
    def __init__(self, font_big, font_small, screen_w, screen_h):
        self.font_big = font_big
        self.font_small = font_small
        self.cxx, self.cyy = screen_w, screen_h
        self.restart_rect = pygame.Rect(screen_w // 2 - 125, screen_h // 2 + 70, 250, 60)
        self.alpha = 0
        self.timer = 0.0
        self.text_actual = None
        
        # Pula tekstów zapobiegająca powtórzeniom i statystycznemu pechowi
        self.all_possible_texts = [
            "STATEK ZOSTAŁ ZDEZINTEGROWANY",
            "TRANSFORMACJA W ZŁOM ZAKOŃCZONA",
            "GRATULACJE! JESTEŚ TERAZ ODPADEM GALAKTYCZNYM",
            "WIEMY ŻE TO NIE TWOJA WINA. TO PRZEZ LAGI",
            "MISJA ZAKOŃCZONA... PO PROSTU NIE TAK, JAK PLANOWAŁEŚ",
            "TWOJE OSTATNIE SŁOWA ZOSTAŁY ZARCHIWIZOWANE JAKO: 'UPS'."
        ]
        self.text_pool = []

        # Przygotowanie powierzchni dla efektu scanlines (raz, dla wydajności)
        self.scanline_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        for y in range(0, screen_h, 3):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 40), (0, y), (screen_w, y))

    def draw(self, window, dt, mouse_pos):
        self.timer += dt
        
        # 1. LOGIKA POJAWIANIA SIĘ I WYBORU TEKSTU
        if self.alpha < 255:
            self.alpha = min(255, self.alpha + 200 * dt)

        if self.text_actual is None:
            # Jeśli pula jest pusta, odświeżamy ją i mieszamy
            if not self.text_pool:
                self.text_pool = self.all_possible_texts.copy()
                random.shuffle(self.text_pool)
            
            # Pobieramy następny unikalny tekst z puli
            self.text_actual = self.text_pool.pop()

        # 2. EFEKT GLITCH I CHROMATIC ABERRATION
        glitch_x = random.uniform(-4, 4) if random.random() < 0.05 else 0
        
        # Rysujemy 3 warstwy tekstu dla efektu rozszczepienia kolorów
        for offset, col in [(2, (255, 0, 0)), (-2, (0, 150, 255)), (0, (255, 255, 255))]:
            surf = self.font_big.render(self.text_actual, True, col)
            
            # Główny tekst biały, warstwy kolorowe są bardziej przezroczyste
            current_alpha = self.alpha if col == (255, 255, 255) else int(self.alpha * 0.4)
            surf.set_alpha(current_alpha)
            
            # Animacja pływania (sinus) + przesunięcie kolorów (offset) + glitch
            pos_x = self.cxx // 2 + offset * math.sin(self.timer * 5) + glitch_x
            pos_y = self.cyy // 2 - 50
            window.blit(surf, surf.get_rect(center=(pos_x, pos_y)))

        # 3. INTERAKTYWNY PRZYCISK RESTART
        is_hover = self.restart_rect.collidepoint(mouse_pos)
        
        # Animacja skali przycisku
        s_target = 1.1 if is_hover else 1.0
        s_val = s_target + math.sin(self.timer * 6) * 0.02 # Pulsowanie
        
        draw_w = int(self.restart_rect.width * s_val)
        draw_h = int(self.restart_rect.height * s_val)
        draw_rect = pygame.Rect(0, 0, draw_w, draw_h)
        draw_rect.center = self.restart_rect.center

        # Poświata przycisku (Bloom)
        if is_hover:
            glow_surf = pygame.Surface((draw_w + 20, draw_h + 20), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (200, 0, 0, 50), (0, 0, draw_w + 20, draw_h + 20), border_radius=15)
            window.blit(glow_surf, glow_surf.get_rect(center=draw_rect.center))

        # Tło i ramka przycisku
        btn_col = (130, 20, 20) if is_hover else (30, 30, 40)
        pygame.draw.rect(window, btn_col, draw_rect, border_radius=12)
        pygame.draw.rect(window, (255, 255, 255) if is_hover else (100, 100, 120), draw_rect, 2, border_radius=12)

        # Tekst na przycisku
        btn_txt = self.font_small.render("RESTART", True, (255, 255, 255))
        txt_alpha = int(200 + 55 * math.sin(self.timer * 12)) if is_hover else 255
        btn_txt.set_alpha(min(self.alpha, txt_alpha))
        window.blit(btn_txt, btn_txt.get_rect(center=draw_rect.center))

        # 4. POST-PROCESSING (SCANLINES)
        window.blit(self.scanline_surf, (0, 0))
        
        # Podpowiedź na samym dole
        hint = self.font_small.render("SYSTEM GOTOWY - NACIŚNIJ [R] LUB KLIKNIJ", True, (120, 120, 130))
        hint.set_alpha(int(abs(math.sin(self.timer * 2)) * self.alpha)) 
        window.blit(hint, hint.get_rect(center=(self.cxx // 2, self.cyy // 2 + 160)))

class GameController:
    def __init__(self, battle: "Battle", event_obj: "Event", player: "SpaceShip", cxx: int, cyy: int, loaded_images: dict, clock: pygame.time.Clock, level_manager: "LevelManager", collision: "Collision", enemy_manager: "EnemyManager", param: "Parameters"):
        self.ui = UI(event_obj, cxx, cyy, loaded_images, battle, player, level_manager, enemy_manager, param)
        self.input_handler = InputHandler(event_obj, player, battle, self.ui, collision, enemy_manager)
        self.clock = clock
        self.event_obj = event_obj
    def update(self, dt: float):
        # Musimy przypisać wynik do zmiennej i go zwrócić!
        result = self.input_handler.update()
        self.ui.update(self.clock.get_fps(), dt)
        
        return result # To pozwoli głównej pętli gry zareagować na "RESTART"

    def draw(self, window: pygame.Surface, camera, dt):
        self.ui.draw(window, camera, (self.event_obj.mouse_x, self.event_obj.mouse_y), dt)


class InputHandler:
    def __init__(self, event_obj: "Event", player_obj: "SpaceShip", player_shoot: "Battle", ui_obj: "UI", collision: "Collision", enemy_manager: "EnemyManager"):
        self.event_obj = event_obj
        self.player_obj = player_obj
        self.player_shoot = player_shoot
        self.ui_obj = ui_obj
        self.ctrl_pressed_last_frame = False
    
    def update(self):
        # Pobieramy aktualny stan myszy bezpośrednio z pygame dla pewności
        mouse_press = self.event_obj.click_left
        mouse_pos = (self.event_obj.mouse_x, self.event_obj.mouse_y)

        if self.ui_obj.is_game_over:
            # 1. Sprawdzenie klawisza R
            if self.event_obj.key_r:
                self.ui_obj.game_over_comp.text_actual = None
                return "RESTART"
            
            # 2. Sprawdzenie kliknięcia myszką w przycisk
            if mouse_press: # Lewy przycisk myszy
                if self.ui_obj.game_over_comp.restart_rect.collidepoint(mouse_pos):
                    # Opcjonalnie: mały delay lub dźwięk przed restartem
                    self.ui_obj.game_over_comp.text_actual = None
                    return "RESTART"
            
            return None
        
        self.ui_obj.reward_1_choosed = self.event_obj.key_o
        self.ui_obj.reward_2_choosed = self.event_obj.key_p

        if self.event_obj.key_r: self.ui_obj.last_celowanie_mode = 1
        elif self.event_obj.key_t: self.ui_obj.last_celowanie_mode = 2
            
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

        for i in range(9):
            if getattr(self.event_obj, f'key_{i+1}'):
                self.player_shoot.select_weapon(i)
                break


class UI:
    """UIManager - Teraz jako czysty koordynator komponentów."""
    def __init__(self, event_obj, cxx, cyy, images, battle, ship, level_manager, enemy_manager, param):
        self.battle, self.space_ship = battle, ship
        self.level_manager, self.enemy_manager = level_manager, enemy_manager
        self.space_ship_parameters = param
        self.cxx, self.cyy = cxx, cyy
        
        # Inicjalizacja czcionek
        try:
            self.font = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 14)
            self.font_big = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 18)
        except:
            self.font = pygame.font.SysFont("Arial", 14, bold=True)
            self.font_big = pygame.font.SysFont("Arial", 18, bold=True)

        # KOMPONENTY
        self.stats = StatsComponent(self.font)
        self.weapons = WeaponComponent(images, 
            ["images/Lasers/laserBlue12.png", "images/Lasers/laserBlue13.png", "images/Lasers/laserBlue14.png", "images/Lasers/laserBlue15.png", "images/Lasers/laserBlue16.png"],
            [f"images/Missiles/spaceMissiles_{p}.png" for p in ["001", "004", "007", "010", "013", "016", "019", "022", "025"]],
            self.font)
        self.targeting = TargetingComponent(self.font, self.font_big, cxx, cyy)
        self.rewards = RewardComponent(self.font, self.font_big, cxx, cyy)

        # Stan
        self.pulse_time = 0
        self.last_celowanie_mode = 1
        self.player_can_manevre = True
        self.show_reward_selection = False
        self.reward_shown_timer = 0
        self.reward_1_choosed = self.reward_2_choosed = False
        self.active_rewards = {}
        self.game_over_comp = GameOverComponent(self.font_big, self.font, cxx, cyy)
        self.is_game_over = False
        self.game_over_delay_timer = 0  # Licznik opóźnienia po zniszczeniu

    def update(self, fps, dt):
        self.pulse_time += dt
        
        # --- LOGIKA OPÓŹNIENIA EKRANU ŚMIERCI ---
        if self.space_ship.is_destroyed and not self.is_game_over:
            self.game_over_delay_timer += dt
            if self.game_over_delay_timer >= 1.0: # 1 sekunda opóźnienia
                self.is_game_over = True
        # ----------------------------------------

        # Update komponentów
        self.stats.update(self.space_ship.hp, self.level_manager.xp, dt)
        self.weapons.update(self.battle, self.cxx, dt)
        self.rewards.update(self.show_reward_selection, dt)
        
        is_active, min_d = self.targeting.update_logic(self.battle, self.enemy_manager, self.space_ship, self.last_celowanie_mode)
        self._target_info = (is_active, min_d)
        
        
        # Logika nagród
        if self.show_reward_selection:
            self.reward_shown_timer += dt
            self._handle_reward_input()
        
        if self.rewards.alpha <= 0 and self.rewards.is_closing:
            self._actually_close_rewards()

    def draw(self, window, camera, mouse_pos, dt):
        # Jeśli flaga is_game_over jest True, rysujemy tylko ekran końcowy
        if self.is_game_over:
            self.game_over_comp.draw(window, dt, mouse_pos)
            return

        # Jeśli statek jest zniszczony, ale czekamy na delay (is_game_over jeszcze False)
        # Możemy tutaj np. przestać rysować celownik, żeby gracz widział tylko wybuch/pustkę
        if not self.space_ship.is_destroyed:
            self.targeting.draw_lock_on(window, camera, self.battle, self.space_ship, self.pulse_time)

        # 2. Górny panel tło
        overlay = pygame.Surface((self.cxx, 115), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 140), (0, 0, self.cxx, 115))
        window.blit(overlay, (0, 0))

        # 3. Bronie i Statystyki
        start_x, total_w = self.weapons.draw(window, self.battle, self.cxx, 25)
        self.stats.draw(window, self.space_ship, self.level_manager, start_x, total_w)
        
        # 4. Skille
        self.weapons.draw_skill_bar(window, start_x - 50, 25, "Shield", 
            self.battle.shield_timer/self.battle.shield_max_timer if self.battle.shield_active else 1.0-(self.battle.shield_cooldown/self.battle.max_shield_cooldown),
            (255, 255, 255) if self.battle.shield_active else (0, 120, 255))
        
        self.weapons.draw_skill_bar(window, start_x + total_w + 30, 25, "Booster", 
            1.0 - (self.space_ship.boost_cooldown / self.space_ship.max_boost_cooldown), (255, 150, 0))

        # 5. Dolne moduły
        is_active, min_d = self._target_info
        theme_col = (255, 50, 50) if self.battle.switch_cooldown > 0 else (0, 220, 255)
        self.targeting.draw_module(window, is_active, min_d, self.last_celowanie_mode, self.pulse_time, theme_col)
        
        # 6. Okno nagród
        self.rewards.draw(window, self.active_rewards)

    # --- METODY POMOCNICZE LOGIKI (Zgodnie z oryginałem) ---

    def rewards_too_choose(self, rewards_data, dt):
        self.player_can_manevre = False
        self.stats.prev_max_xp = self.level_manager.xp
        
        act1, txt1 = self._get_upgrade_action(rewards_data.get("reward_1", {}))
        act2, txt2 = self._get_upgrade_action(rewards_data.get("reward_2", {}))
        
        self.active_rewards = {"1": {"action": act1, "text": txt1}, "2": {"action": act2, "text": txt2}}
        self.show_reward_selection = True
        self.reward_shown_timer = 0
        self.rewards.is_closing = False

    def _handle_reward_input(self):
        if self.reward_shown_timer < 1.0: return
        
        if self.reward_1_choosed:
            self.active_rewards["1"]["action"]()
            self._close_rewards()
        elif self.reward_2_choosed:
            self.active_rewards["2"]["action"]()
            self._close_rewards()

    def _close_rewards(self):
        self.rewards.is_closing = True
        self.show_reward_selection = False

    def _actually_close_rewards(self):
        self.rewards.is_closing = False
        self.active_rewards = {}
        self.enemy_manager.can_start_new_level = True
        self.player_can_manevre = True

    def _get_upgrade_action(self, data):
        m_map = {
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
            "reduce_max_shield_cooldown": self.space_ship_parameters.reduce_max_shield_cooldown,
            "add_shield_max_timer": self.space_ship_parameters.add_shield_max_timer,
            "reduce_linear_friction": self.space_ship_parameters.reduce_linear_friction,
            "add_braking_force": self.space_ship_parameters.add_braking_force,
            "add_max_boost_cooldown": self.space_ship_parameters.add_max_boost_cooldown,
            "add_hp_reg_speed": self.space_ship_parameters.add_hp_reg_speed,
            "add_max_hp": self.space_ship_parameters.add_max_hp,
            "add_max_speed": self.space_ship_parameters.add_max_speed,
            "add_boost_speed": self.space_ship_parameters.add_boost_speed,
            "add_thrust_power": self.space_ship_parameters.add_thrust_power,
            "add_idle_friction": self.space_ship_parameters.add_idle_friction          
        }
        for k, v in data.items():
            if k in m_map:
                txt = data.get("text", "Bonus").replace("{var}", str(v))
                return (lambda k=k, v=v: m_map[k](v)), txt
        return (lambda: None), "Błąd danych"