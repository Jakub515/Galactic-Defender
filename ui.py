import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from space_ship import SpaceShip
    from space_ship import Battle
    from functions import Event

class GameController:
    def __init__(self, battle: "Battle", event_obj: "Event", player: "SpaceShip", cxx: int, cyy: int, loaded_images: dict, clock: pygame.time.Clock):
        # Inicjalizujemy UI
        self.ui = UI(event_obj, cxx, cyy, loaded_images)
        # Inicjalizujemy InputHandler i przekazujemy mu obiekt UI
        self.input_handler = InputHandler(event_obj, player, battle, self.ui)
        # Przechowujemy referencję do zegara gry
        self.clock = clock

    def update(self, dt: float):
        self.input_handler.update()
        # Przekazujemy aktualny FPS do UI
        self.ui.update(self.clock.get_fps())

    def draw(self, window: pygame.Surface):
        self.ui.draw(window)

class InputHandler:
    def __init__(self, event_obj: "Event", player_obj: "SpaceShip", player_shoot:"Battle", ui_obj: "UI"):
        self.event_obj = event_obj
        self.player_obj = player_obj
        self.ctrl_pressed_last_frame = False
        self.player_shoot = player_shoot
        self.ui_obj = ui_obj
    
    def update(self):
        # --- RUCH ---
        is_boosting = self.event_obj.backquote
        self.player_obj.thrust(self.event_obj.key_up, boost=is_boosting)

        # Rotacja
        if self.event_obj.key_left:
            self.player_obj.rotate(1)
        elif self.event_obj.key_right:
            self.player_obj.rotate(-1)
        else:
            self.player_obj.rotate(0)

        # Hamowanie
        self.player_obj.brake(self.event_obj.key_down)

        # --- WALKA ---
        self.player_shoot.fire(self.event_obj.key_space)

        if self.event_obj.key_s:
            self.player_shoot.activate_shield()

        if self.event_obj.key_ctrl_left and not self.ctrl_pressed_last_frame:
            self.player_shoot.switch_weapon_set()
            self.ui_obj.change_weapon_type_ctr()
        self.ctrl_pressed_last_frame = self.event_obj.key_ctrl_left

        keys_numbers = [
            self.event_obj.key_1, self.event_obj.key_2, self.event_obj.key_3,
            self.event_obj.key_4, self.event_obj.key_5, self.event_obj.key_6,
            self.event_obj.key_7, self.event_obj.key_8, self.event_obj.key_9
        ]
        
        for i, pressed in enumerate(keys_numbers):
            if pressed:
                self.ui_obj.change_weapon_type_num(i)
                self.player_shoot.select_weapon(i)
                break

class UI:
    def __init__(self, event_obj: "Event", screen_width: int, screen_height: int, images: dict):
        self.event_obj = event_obj
        self.cxx = screen_width
        self.cyy = screen_height
        
        # Próba załadowania czcionki, fallback do systemowej w razie błędu
        try:
            self.font = pygame.font.Font("fonts/JetBrainsMono-Italic-VariableFont_wght.ttf", 16)
        except:
            self.font = pygame.font.SysFont("Arial", 16, bold=True)

        self.weapons = self.setup_weapons_1(images)
        self.weapons_2 = self.setup_weapons_2(images)

        self.active_set = 1
        self.current_weapon = 0
        self.fps = 0
        
        # --- PARAMETRY GRAFICZNE ---
        self.slot_size = 55
        self.spacing = 8
        self.y_pos = 25
        
        # --- LOGIKA ANIMACJI ---
        self.frame_x = 0
        self.target_x = 0
        self.lerp_speed = 0.15

    def setup_weapons_1(self, images: dict):
        return [
            [images["images/Lasers/laserBlue12.png"], 60, 5, 0.1],
            [images["images/Lasers/laserBlue13.png"], 65, 4, 0.4],
            [images["images/Lasers/laserBlue14.png"], 70, 3, 0.3],
            [images["images/Lasers/laserBlue15.png"], 75, 2, 0.2],
            [images["images/Lasers/laserBlue16.png"], 80, 1, 0.1]
        ]

    def setup_weapons_2(self, images: dict):
        paths = ["001", "004", "007", "010", "013", "016", "019", "022", "025"]
        return [[images[f"images/Missiles/spaceMissiles_{p}.png"], 40, 5, 3] for p in paths]

    def change_weapon_type_ctr(self):
        self.active_set = 2 if self.active_set == 1 else 1
        self.current_weapon = 0

    def change_weapon_type_num(self, index: int):
        current_list = self.weapons if self.active_set == 1 else self.weapons_2
        if index < len(current_list):
            self.current_weapon = index

    def draw_proportional_icon(self, window: pygame.Surface, icon: pygame.Surface, rect: pygame.Rect):
        img_w, img_h = icon.get_size()
        padding = 10
        max_dim = self.slot_size - padding
        scale = min(max_dim / img_w, max_dim / img_h)
        
        new_size = (int(img_w * scale), int(img_h * scale))
        scaled_icon = pygame.transform.smoothscale(icon, new_size)
        icon_rect = scaled_icon.get_rect(center=rect.center)
        window.blit(scaled_icon, icon_rect)

    def update(self, current_fps: float):
        """Przeliczanie pozycji animowanej ramki oraz FPS"""
        self.fps = current_fps
        current_list = self.weapons if self.active_set == 1 else self.weapons_2
        
        total_w = len(current_list) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2
        
        self.target_x = start_x + self.current_weapon * (self.slot_size + self.spacing)
        
        if abs(self.target_x - self.frame_x) > 400:
            self.frame_x = self.target_x
            
        self.frame_x += (self.target_x - self.frame_x) * self.lerp_speed

    def draw(self, window: pygame.Surface):
        # 1. Rysowanie FPS w prawym górnym rogu
        fps_text = self.font.render(f"FPS: {int(self.fps)}", True, (0, 255, 100))
        # topright zapewnia stały margines od prawej krawędzi
        window.blit(fps_text, (self.cxx - fps_text.get_width() - 20, 20))

        # 2. Rysowanie slotów i ikon
        current_list = self.weapons if self.active_set == 1 else self.weapons_2
        total_w = len(current_list) * (self.slot_size + self.spacing) - self.spacing
        start_x = (self.cxx - total_w) // 2

        for i, weapon_data in enumerate(current_list):
            icon = weapon_data[0]
            x = start_x + i * (self.slot_size + self.spacing)
            slot_rect = pygame.Rect(x, self.y_pos, self.slot_size, self.slot_size)
            
            s = pygame.Surface((self.slot_size, self.slot_size), pygame.SRCALPHA)
            pygame.draw.rect(s, (20, 20, 30, 180), (0, 0, self.slot_size, self.slot_size), border_radius=5)
            window.blit(s, (x, self.y_pos))
            
            pygame.draw.rect(window, (80, 80, 100), slot_rect, 1, border_radius=5)
            self.draw_proportional_icon(window, icon, slot_rect)

            key_label = self.font.render(str(i + 1), True, (200, 200, 200))
            window.blit(key_label, (x + 5, self.y_pos + 2))

        # 3. Rysowanie animowanej ramki wyboru
        glow_rect = pygame.Rect(self.frame_x - 2, self.y_pos - 2, self.slot_size + 4, self.slot_size + 4)
        pygame.draw.rect(window, (0, 200, 255), glow_rect, 3, border_radius=6)
        
        # 4. Tryb broni pod paskiem
        mode_name = "SYSTEM LASEROWY" if self.active_set == 1 else "WYRZUTNIA RAKIET"
        mode_txt = self.font.render(mode_name, True, (0, 255, 255))
        window.blit(mode_txt, (self.cxx // 2 - mode_txt.get_width() // 2, self.y_pos + self.slot_size + 5))