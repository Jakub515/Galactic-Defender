import pygame
import json
import threading
from queue import Queue

# Importy modułów
import jednostki.space_ship as space_ship
import utils.collisions as collisions
import jednostki.shoot as shoot
import ui.radar as radar
import ui.ui as ui
import core.level_manager as level_manager
from .camera import Camera
from jednostki.enemy_ship import EnemyManager
from jednostki.asteroids import AsteroidManager

class Game:
    def __init__(self, screen_width: int, screen_height: int, 
                 gfx_40: dict, gfx_100: dict, audio_files: list, 
                 music_obj, events_obj, clock):
        
        # --- System ładowania ---
        self.loading_queue = Queue()
        self.is_loading = False
        self.loading_status = "INITIALIZING..."
        
        # Czcionki do UI ładowania
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20)

        # --- Atrybuty podstawowe ---
        self.cxx = screen_width
        self.cyy = screen_height
        self.clock = clock
        self.music_obj = music_obj
        self.events_obj = events_obj
        self.gfx_40 = gfx_40
        self.gfx_100 = gfx_100
        self.audio_files = audio_files
        
        self.paused = False
        self.was_updated_initially = False

        # Uruchomienie pierwszego ładowania podczas initu
        self.start_async_load(self.initial_load_task, status_text="BOOTING SYSTEM...")

    # --- LOGIKA ŁADOWANIA ASYNCHRONICZNEGO ---

    def start_async_load(self, task_func, *args, flag_load_level_f5=True, status_text="LOADING..."):
        """Uruchamia proces ładowania w tle z określonym statusem."""
        self.is_loading = True
        self.loading_status = status_text
        
        if flag_load_level_f5:
            thread = threading.Thread(target=task_func, args=(), daemon=True)
        else:
            thread = threading.Thread(target=task_func, args=args, daemon=True)
        thread.start()

    def initial_load_task(self):
        """Pełna inicjalizacja obiektów gry przy starcie."""
        self.WORLD_CENTER = pygame.math.Vector2(0, 0)
        
        with open('./data/level_slownik.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        level_data = data.get("level_1", {})
        world_config = level_data.get("world_config", {})
        self.WORLD_RADIUS = world_config.get("word_radius", 2500)
        
        self.pola_asteroid = []
        raw_asteroids = world_config.get("asteroid_data", [])
        for entry in raw_asteroids:
            aster_zone = {
                "pos": pygame.math.Vector2(entry.get("center_x", 0), entry.get("center_y", 0)),
                "radius": entry.get("radius", 1000),
                "count": entry.get("count", 20)
            }
            self.pola_asteroid.append(aster_zone)
            
        self.FADE_ZONE = 2000
        self.dist = 0

        # Inicjalizacja systemów
        self.shoot_obj = shoot.Shoot(self.gfx_40)
        self.camera = Camera(self.cxx, self.cyy, lerp_factor=0.08, offset_scalar=15)
        self.player_parameters = space_ship.Parameters(self.gfx_40)

        self.player = space_ship.SpaceShip(
            self.gfx_40, self.audio_files, self.cxx, self.cyy, [0, 0], 
            self.music_obj, self.shoot_obj, self.player_parameters
        )
        self.player_shoot = space_ship.Battle(
            self.player, self.gfx_40, self.audio_files, self.cxx, self.cyy, [0, 0], 
            self.music_obj, self.shoot_obj, self.player_parameters
        )

        self.asteroid_manager = AsteroidManager(self.gfx_100, self.pola_asteroid, self.WORLD_RADIUS)

        self.enemy_manager = EnemyManager(
            self.gfx_40, self.player, self.music_obj, 5, 
            self.shoot_obj, self.WORLD_RADIUS, self.asteroid_manager
        )

        self.colision_obj = collisions.Collision(self.music_obj, self.cxx, self.cyy, self.enemy_manager, self.WORLD_RADIUS)
        self.radar_obj = radar.Radar(self.cxx, self.cyy, 200, self.WORLD_RADIUS)
        self.level_manager = level_manager.LevelManager(self.enemy_manager)
        
        self.game_controller = ui.GameController(
            self.player_shoot, self.events_obj, self.player, 
            self.cxx, self.cyy, self.gfx_100, self.clock, 
            self.level_manager, self.colision_obj, self.enemy_manager, self.player_parameters
        )
        self.level_manager.init_additional_settings(self.game_controller.ui)
        
        self.loading_queue.put("DONE")

    def reset_task(self):
        """Zadanie resetu (F5)."""
        data_to_load = self.reset_to_level_one()
        self.level_load_task(data_to_load)

    def level_load_task(self, data_to_load):
        """Przeładowanie parametrów poziomu."""
        self.WORLD_RADIUS = data_to_load[0]
        self.player.reinit_pos()
        self.asteroid_manager.reinit_asteroid_data(data_to_load[1], self.WORLD_RADIUS)
        self.radar_obj.world_radius = self.WORLD_RADIUS
        self.colision_obj.reload_world_radius(self.WORLD_RADIUS)
        self.shoot_obj.shots = []
        self.loading_queue.put("DONE")

    def reset_to_level_one(self):
        """Reset logiki do stanu początkowego."""
        self.player.hp = self.player_parameters.max_hp
        self.player.is_destroyed = False
        self.player.player_pos = pygame.math.Vector2(0, 0)
        self.player.velocity = pygame.math.Vector2(0, 0)
        
        self.game_controller.ui.is_game_over = False
        self.game_controller.ui.game_over_comp.alpha = 0
        self.game_controller.ui.stats.displayed_hp = self.player.hp
        self.game_controller.ui.stats.displayed_xp = 0
        self.game_controller.ui.player_can_manevre = True 
        self.game_controller.ui.game_over_delay_timer = 0
        
        return self.level_manager.reset_to_start()

    # --- PĘTLA GŁÓWNA ---

    def mainloop(self, dt: float):
        if self.is_loading:
            try:
                msg = self.loading_queue.get_nowait()
                if msg == "DONE":
                    self.is_loading = False
            except:
                self.was_updated_initially = False
            return 
        
        else:
            self.was_updated_initially = True
        
        
        
        # Kontroler UI (Restart / Sterowanie)
        controller_status = self.game_controller.update(dt)
        if controller_status == "RESTART":
            self.start_async_load(self.reset_task, status_text="RESTARTING SECTOR...")
            return 
            
        # Logika poziomów
        data_to_load = self.level_manager.update(dt)
        if data_to_load is not None:
            self.start_async_load(self.level_load_task, data_to_load, flag_load_level_f5=False, status_text="LOADING NEXT LEVEL...")
            return

        # Update fizyki i jednostek
        self.player.update(dt)
        self.player_shoot.update(dt, self.enemy_manager)
        self.enemy_manager.update(dt)
        self.asteroid_manager.update(dt, self.player, self.enemy_manager)
        self.shoot_obj.update(self.enemy_manager, self.music_obj)
        
        # Bariera świata
        self.dist = self.player.player_pos.distance_to(self.WORLD_CENTER)
        if self.dist > self.WORLD_RADIUS:
            self.player.player_pos = self.WORLD_CENTER + (self.player.player_pos - self.WORLD_CENTER).normalize() * self.WORLD_RADIUS
            self.player.velocity *= -0.3
            self.player.hp = 0 

        self.colision_obj.check_collisions(
            self.player_shoot, self.player, self.enemy_manager, 
            self.shoot_obj, self.asteroid_manager, self.level_manager
        )
        
        self.camera.update(self.player.player_pos, self.player.velocity)

    # --- RENDEROWANIE ---

    def draw_loading_screen(self, window):
        """Renderuje dedykowany ekran ładowania."""
        window.fill((5, 5, 15)) # Bardzo ciemny granatowy
        
        # Tekst główny
        load_surf = self.font_large.render("LOADING", True, (255, 255, 255))
        load_rect = load_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 - 40))
        
        # Tekst statusu
        status_surf = self.font_small.render(self.loading_status, True, (100, 150, 255))
        status_rect = status_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 + 20))
        
        # Animacja paska (sinusoida czasowa)
        bar_width = 300
        progress = (pygame.time.get_ticks() / 1000) % 1.0 # 0.0 do 1.0
        
        # Tło paska
        pygame.draw.rect(window, (30, 30, 50), (self.cxx//2 - bar_width//2, self.cyy//2 + 50, bar_width, 4))
        # Aktywny segment paska
        active_w = 60
        pos_x = (self.cxx//2 - bar_width//2) + (bar_width - active_w) * progress
        pygame.draw.rect(window, (0, 200, 255), (pos_x, self.cyy//2 + 50, active_w, 4))

        window.blit(load_surf, load_rect)
        window.blit(status_surf, status_rect)

    def draw(self, window: pygame.Surface, dt: float):
        if self.is_loading:
            self.draw_loading_screen(window)
            return  
        
        if not self.was_updated_initially:
            return

        # 1. Bariera świata
        if self.dist > self.WORLD_RADIUS - self.FADE_ZONE:
            alpha = int(max(0, min(1.0, (self.dist - (self.WORLD_RADIUS - self.FADE_ZONE)) / self.FADE_ZONE)) * 255)
            rel_center = self.camera.apply(self.WORLD_CENTER)
            temp_s = pygame.Surface((self.cxx, self.cyy), pygame.SRCALPHA)
            pygame.draw.circle(temp_s, (255, 0, 0, alpha // 4), rel_center, self.WORLD_RADIUS, 500)
            pygame.draw.circle(temp_s, (255, 50, 50, alpha), rel_center, self.WORLD_RADIUS, 15)
            window.blit(temp_s, (0, 0))

        # 2. Obiekty świata
        off_x, off_y = self.camera.offset.x, self.camera.offset.y
        self.shoot_obj.draw(window, off_x, off_y)
        self.asteroid_manager.draw(window, off_x, off_y, self.cxx, self.cyy)
        self.enemy_manager.draw(window, off_x, off_y)
        
        # 3. Gracz
        p_draw = self.camera.apply(self.player.player_pos)
        self.player.draw(window, p_draw[0], p_draw[1])
        self.player_shoot.draw(window, p_draw[0], p_draw[1])

        # 4. Interfejs
        self.radar_obj.draw(window, self.player, self.enemy_manager, self.asteroid_manager, dt, self.player_shoot)
        self.game_controller.draw(window, self.camera, dt)