import pygame
import json
import jednostki.space_ship as space_ship
import utils.collisions as collisions
import jednostki.shoot as shoot
import ui.radar as radar
import ui.ui as ui
import core.level_manager as level_manager
from .camera import Camera
from jednostki.enemy_ship import EnemyManager
from jednostki.asteroids import AsteroidManager
from .thread_helper import LoadingManager 

# --- KLASA EKRANU ŁADOWANIA ---
class LoadingScreen:
    def __init__(self, screen_width: int, screen_height: int):
        self.cxx = screen_width
        self.cyy = screen_height
        
        # Inicjalizacja czcionek
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20)

        # Parametry animacji paska
        self.display_progress = 0.0  # To co widzi gracz (0.0 do 1.0)
        self.target_fake_max = 0.92  # Do ilu % pasek ma "pełznąć" czekając na wątek
        self.bar_width = 500         # Dłuższy pasek

    def reset(self):
        """Resetuje stan paska przed nowym ładowaniem."""
        self.display_progress = 0.0

    def draw(self, window: pygame.Surface, status_text: str, is_actually_done: bool):
        """
        Renderuje wizualną część ładowania.
        is_actually_done: informacja czy wątek w tle skończył pracę.
        """
        window.fill((5, 5, 15)) # Bardzo ciemny granatowy
        
        # --- LOGIKA POSTĘPU ---
        if not is_actually_done:
            # Pasek dąży do target_fake_max, ale zwalnia (progres logarytmiczny)
            diff = self.target_fake_max - self.display_progress
            self.display_progress += diff * 0.015  # Prędkość pełzania
        else:
            # Gwałtowny finisz po zakończeniu ładowania danych
            self.display_progress += (1.05 - self.display_progress) * 0.1
            if self.display_progress > 1.0: 
                self.display_progress = 1.0

        # --- RENDERING ---
        # Tekst główny
        load_surf = self.font_large.render("SYSTEM INITIALIZATION", True, (255, 255, 255))
        load_rect = load_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 - 50))
        
        # Tekst statusu
        status_surf = self.font_small.render(status_text, True, (100, 150, 255))
        status_rect = status_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 + 30))
        
        # Rysowanie paska (Tło)
        bx = self.cxx // 2 - self.bar_width // 2
        by = self.cyy // 2 + 70
        bh = 10
        pygame.draw.rect(window, (20, 20, 40), (bx - 4, by - 4, self.bar_width + 8, bh + 8), 2) # Ramka
        pygame.draw.rect(window, (30, 30, 50), (bx, by, self.bar_width, bh)) # Tło paska
        
        # Rysowanie paska (Wypełnienie)
        current_w = int(self.bar_width * self.display_progress)
        if current_w > 0:
            # Główny kolor
            pygame.draw.rect(window, (0, 180, 255), (bx, by, current_w, bh))
            # Animowany "odblask" na czole paska
            glow_w = min(20, current_w)
            pygame.draw.rect(window, (180, 240, 255), (bx + current_w - glow_w, by, glow_w, bh))

        # Procenty
        perc_surf = self.font_small.render(f"{int(self.display_progress * 100)}%", True, (255, 255, 255))
        window.blit(perc_surf, (bx + self.bar_width + 15, by - 5))

        window.blit(load_surf, load_rect)
        window.blit(status_surf, status_rect)


# --- GŁÓWNA KLASA GRY ---
class Game:
    def __init__(self, screen_width: int, screen_height: int, 
                 gfx_40: dict, gfx_100: dict, audio_files: list, 
                 music_obj, events_obj, clock):
        
        # 1. System ładowania i wizualizacji
        self.loader = LoadingManager(screen_width, screen_height)
        self.loading_screen = LoadingScreen(screen_width, screen_height)
        
        # 2. Atrybuty podstawowe
        self.cxx, self.cyy = screen_width, screen_height
        self.clock, self.music_obj, self.events_obj = clock, music_obj, events_obj
        self.gfx_40, self.gfx_100, self.audio_files = gfx_40, gfx_100, audio_files
        
        self.paused = False
        self.was_updated_initially = False
        self.WORLD_CENTER = pygame.math.Vector2(0, 0)
        self.FADE_ZONE = 2000
        self.dist = 0
        
        self.last_f5_state = False

        # Start pierwszego ładowania
        self.start_loading(self.initial_load_task, "BOOTING SYSTEM...")

    def start_loading(self, task, status_text, *args):
        """
        Pomocnicza metoda do resetu paska i startu wątku.
        *args pozwala przekazać dowolną liczbę argumentów do zadania (task).
        """
        self.loading_screen.reset()
        # Przekazujemy args bezpośrednio do managera
        self.loader.start_async_load(task, *args, status_text=status_text)

    # --- ZADANIA DLA WĄTKÓW ---

    def initial_load_task(self):
        """Wczytywanie wszystkich zasobów przy starcie."""
        with open('./data/level_slownik.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        level_data = data.get("level_1", {})
        world_config = level_data.get("world_config", {})
        self.WORLD_RADIUS = world_config.get("word_radius", 2500)
        
        self.pola_asteroid = [{"pos": pygame.math.Vector2(e.get("center_x", 0), e.get("center_y", 0)),
                               "radius": e.get("radius", 1000), "count": e.get("count", 20)}
                              for e in world_config.get("asteroid_data", [])]

        self.shoot_obj = shoot.Shoot(self.gfx_40)
        self.camera = Camera(self.cxx, self.cyy, 0.08, 15)
        self.player_parameters = space_ship.Parameters(self.gfx_40)

        self.player = space_ship.SpaceShip(self.gfx_40, self.audio_files, self.cxx, self.cyy, [0, 0], 
                                          self.music_obj, self.shoot_obj, self.player_parameters)
        self.player_shoot = space_ship.Battle(self.player, self.gfx_40, self.audio_files, self.cxx, self.cyy, [0, 0], 
                                              self.music_obj, self.shoot_obj, self.player_parameters)

        self.asteroid_manager = AsteroidManager(self.gfx_100, self.pola_asteroid, self.WORLD_RADIUS)
        self.enemy_manager = EnemyManager(self.gfx_40, self.player, self.music_obj, 5, 
                                          self.shoot_obj, self.WORLD_RADIUS, self.asteroid_manager)

        self.colision_obj = collisions.Collision(self.music_obj, self.cxx, self.cyy, self.enemy_manager, self.WORLD_RADIUS)
        self.radar_obj = radar.Radar(self.cxx, self.cyy, 200, self.WORLD_RADIUS)
        self.level_manager = level_manager.LevelManager(self.enemy_manager)
        
        self.game_controller = ui.GameController(self.player_shoot, self.events_obj, self.player, 
                                                self.cxx, self.cyy, self.gfx_100, self.clock, 
                                                self.level_manager, self.colision_obj, self.enemy_manager, self.player_parameters)
        self.level_manager.init_additional_settings(self.game_controller.ui)
        
        self.loader.loading_queue.put("DONE")

    def reset_task(self):
        data = self.reset_logic()
        self.level_load_task(data)

    def level_load_task(self, data_to_load):
        self.WORLD_RADIUS = data_to_load[0]
        self.player.reinit_pos()
        self.asteroid_manager.reinit_asteroid_data(data_to_load[1], self.WORLD_RADIUS)
        self.radar_obj.world_radius = self.WORLD_RADIUS
        self.colision_obj.reload_world_radius(self.WORLD_RADIUS)
        self.shoot_obj.shots = []
        self.loader.loading_queue.put("DONE")

    def reset_logic(self):
        self.player.hp = self.player_parameters.max_hp
        self.player.is_destroyed = False
        self.player.player_pos *= 0
        self.player.velocity *= 0
        
        ui_ref = self.game_controller.ui
        ui_ref.is_game_over = False
        ui_ref.game_over_comp.alpha = 0
        ui_ref.stats.displayed_hp = self.player.hp
        ui_ref.stats.displayed_xp = 0
        ui_ref.player_can_manevre = True 
        ui_ref.game_over_delay_timer = 0
        return self.level_manager.reset_to_start()

    # --- PĘTLA GŁÓWNA ---

    def mainloop(self, dt: float):
        # Sprawdzanie statusu wątku ładowania
        if self.loader.is_loading:
            self.loader.check_finished()
        
        # Jeśli pasek jeszcze nie dojechał do 100%, blokujemy logikę gry
        if self.loading_screen.display_progress < 1.0:
            return 
        
        # Flaga aktywująca grę po pierwszym pełnym naładowaniu
        self.was_updated_initially = True
        
        if self.paused: return
        
        # Status z UI (przycisk Restart)
        status = self.game_controller.update(dt)
        if status == "RESTART":
            self.start_loading(self.reset_task, "RESTARTING SECTOR...")
            return 
            
        # Logika poziomów (przejście dalej)
        lvl_data = self.level_manager.update(dt)
        if lvl_data is not None:
            self.start_loading(self.level_load_task, "LOADING NEXT LEVEL...", lvl_data)
            return
        
        # Obsługa klawisza F5
        if self.events_obj.key_f5 and not self.last_f5_state:
            if not self.loader.is_loading:
                self.start_loading(self.reset_task, "REBOOTING...")
        self.last_f5_state = self.events_obj.key_f5

        # Update systemów gry
        self.player.update(dt)
        self.player_shoot.update(dt, self.enemy_manager)
        self.enemy_manager.update(dt)
        self.asteroid_manager.update(dt, self.player, self.enemy_manager)
        self.shoot_obj.update(self.enemy_manager, self.music_obj)
        
        # Bariera mapy
        self.dist = self.player.player_pos.distance_to(self.WORLD_CENTER)
        if self.dist > self.WORLD_RADIUS:
            self.player.player_pos = self.WORLD_CENTER + (self.player.player_pos - self.WORLD_CENTER).normalize() * self.WORLD_RADIUS
            self.player.velocity *= -0.3
            self.player.hp = 0 

        self.colision_obj.check_collisions(self.player_shoot, self.player, self.enemy_manager, 
                                          self.shoot_obj, self.asteroid_manager, self.level_manager)
        self.camera.update(self.player.player_pos, self.player.velocity)

    def draw(self, window: pygame.Surface, dt: float):
        # Jeśli pasek postępu nie skończył animacji, rysuj ekran ładowania
        if self.loading_screen.display_progress < 1.0:
            # Przekazujemy czy wątek tła już skończył (is_loading == False)
            self.loading_screen.draw(window, self.loader.loading_status, not self.loader.is_loading)
            return  
        
        if not self.was_updated_initially: 
            return

        # Renderowanie efektów bariery
        if self.dist > self.WORLD_RADIUS - self.FADE_ZONE:
            alpha = int(max(0, min(1.0, (self.dist - (self.WORLD_RADIUS - self.FADE_ZONE)) / self.FADE_ZONE)) * 255)
            rel_center = self.camera.apply(self.WORLD_CENTER)
            temp_s = pygame.Surface((self.cxx, self.cyy), pygame.SRCALPHA)
            pygame.draw.circle(temp_s, (255, 0, 0, alpha // 4), rel_center, self.WORLD_RADIUS, 500)
            pygame.draw.circle(temp_s, (255, 50, 50, alpha), rel_center, self.WORLD_RADIUS, 15)
            window.blit(temp_s, (0, 0))

        # Renderowanie świata
        ox, oy = self.camera.offset.x, self.camera.offset.y
        self.shoot_obj.draw(window, ox, oy)
        self.asteroid_manager.draw(window, ox, oy, self.cxx, self.cyy)
        self.enemy_manager.draw(window, ox, oy)
        
        # Gracz i UI
        p_draw = self.camera.apply(self.player.player_pos)
        self.player.draw(window, p_draw[0], p_draw[1])
        self.player_shoot.draw(window, p_draw[0], p_draw[1])

        self.radar_obj.draw(window, self.player, self.enemy_manager, self.asteroid_manager, dt, self.player_shoot)
        self.game_controller.draw(window, self.camera, dt)