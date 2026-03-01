import pygame
import os

# Importy Twoich modułów
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
        """
        Główna klasa logiki gry.
        :param screen_width: Szerokość okna (cxx)
        :param screen_height: Wysokość okna (cyy)
        :param gfx_40: Słownik obrazów przeskalowanych do 40%
        :param gfx_100: Słownik obrazów przeskalowanych do 100%
        :param audio_files: Lista ścieżek do plików dźwiękowych
        :param music_obj: Instancja MusicManager
        :param events_obj: Instancja Event
        :param clock: Obiekt pygame.time.Clock
        """
        # --- Atrybuty podstawowe ---
        self.cxx = screen_width
        self.cyy = screen_height
        self.clock = clock
        self.music_obj = music_obj
        self.events_obj = events_obj
        
        # --- Konfiguracja Świata ---
        self.WORLD_CENTER = pygame.math.Vector2(0, 0)
        self.WORLD_RADIUS = 25_000
        self.FADE_ZONE = 2000
        self.dist = 0  # Dystans gracza od środka świata
        
        # --- Inicjalizacja Systemów ---
        self.shoot_obj = shoot.Shoot(gfx_40)
        self.camera = Camera(self.cxx, self.cyy, lerp_factor=0.08, offset_scalar=15)
        self.player_parameters = space_ship.Parameters(gfx_40)
        
        # --- Gracz ---
        self.player = space_ship.SpaceShip(
            gfx_40, audio_files, self.cxx, self.cyy, [0, 0], 
            self.music_obj, self.shoot_obj, self.player_parameters
        )
        self.player_shoot = space_ship.Battle(
            self.player, gfx_40, audio_files, self.cxx, self.cyy, [0, 0], 
            self.music_obj, self.shoot_obj, self.player_parameters
        )

        # --- Zarządzanie Obiektami ---
        self.pola_asteroid = [
            {"pos": pygame.math.Vector2(0, 0), "radius": 22000, "count": 250},
            {"pos": pygame.math.Vector2(0, 0), "radius": 4500, "count": 50}
        ]
        self.asteroid_manager = AsteroidManager(gfx_100, self.pola_asteroid)
        self.enemy_manager = EnemyManager(
            gfx_40, self.player, self.music_obj, 5, 
            self.shoot_obj, self.WORLD_RADIUS, self.asteroid_manager
        )

        # --- UI i Systemy Pomocnicze ---
        self.colision_obj = collisions.Collision(self.music_obj, self.cxx, self.cyy, self.enemy_manager)
        self.radar_obj = radar.Radar(self.cxx, self.cyy, 200, self.WORLD_RADIUS)
        self.level_manager = level_manager.LevelManager(self.enemy_manager)
        
        self.game_controller = ui.GameController(
            self.player_shoot, self.events_obj, self.player, 
            self.cxx, self.cyy, gfx_100, self.clock, 
            self.level_manager, self.colision_obj, self.enemy_manager, self.player_parameters
        )
        
        # Inicjalizacja dodatkowych ustawień UI
        self.level_manager.init_additional_settings(self.game_controller.ui)
        
        # Stan gry
        self.paused = False

    def pause_or_resume(self):
        """Przełącza stan pauzy."""
        self.paused = not self.paused

    def mainloop(self, dt: float):
        """Aktualizacja logiki gry."""
        if self.paused:
            return

        # 1. Update managerów i obiektów
        self.level_manager.update(dt)
        self.game_controller.update(dt)
        self.player.update(dt)
        self.player_shoot.update(dt, self.enemy_manager)
        self.enemy_manager.update(dt)
        self.asteroid_manager.update(dt, self.player, self.enemy_manager)
        self.shoot_obj.update(self.enemy_manager)
        
        # 2. Fizyka bariery świata
        self.dist = self.player.player_pos.distance_to(self.WORLD_CENTER)
        if self.dist > self.WORLD_RADIUS:
            # Odbicie i powrót do granicy
            self.player.player_pos = self.WORLD_CENTER + (self.player.player_pos - self.WORLD_CENTER).normalize() * self.WORLD_RADIUS
            self.player.velocity *= -0.3
            self.player.destroy_cause_collision()

        # 3. Kolizje
        self.colision_obj.check_collisions(
            self.player_shoot, self.player, self.enemy_manager, 
            self.shoot_obj, self.asteroid_manager, self.level_manager
        )
        
        # 4. Kamera
        self.camera.update(self.player.player_pos, self.player.velocity)

    def draw(self, window: pygame.Surface, dt: float):
        """Renderowanie wszystkich elementów gry na podaną powierzchnię."""
        
        # --- 1. Bariera świata (Glow efekt) ---
        if self.dist > self.WORLD_RADIUS - self.FADE_ZONE:
            # Obliczanie przezroczystości (fade in) przy zbliżaniu się do granicy
            alpha = int(max(0, min(1.0, (self.dist - (self.WORLD_RADIUS - self.FADE_ZONE)) / self.FADE_ZONE)) * 255)
            rel_center = self.camera.apply(self.WORLD_CENTER)
            
            # Tworzenie tymczasowej powierzchni dla przezroczystości
            temp_s = pygame.Surface((self.cxx, self.cyy), pygame.SRCALPHA)
            # Gruby, lekki okrąg (aura)
            pygame.draw.circle(temp_s, (255, 0, 0, alpha // 4), rel_center, self.WORLD_RADIUS, 500)
            # Cienka, mocniejsza linia graniczna
            pygame.draw.circle(temp_s, (255, 50, 50, alpha), rel_center, self.WORLD_RADIUS, 15)
            window.blit(temp_s, (0, 0))

        # --- 2. Obiekty świata (podążają za kamerą) ---
        off_x, off_y = self.camera.offset.x, self.camera.offset.y
        
        self.shoot_obj.draw(window, off_x, off_y)
        self.asteroid_manager.draw(window, off_x, off_y, self.cxx, self.cyy)
        self.enemy_manager.draw(window, off_x, off_y)
        
        # --- 3. Gracz (pozycja relatywna do kamery) ---
        p_draw = self.camera.apply(self.player.player_pos)
        self.player.draw(window, p_draw[0], p_draw[1])
        self.player_shoot.draw(window, p_draw[0], p_draw[1])

        # --- 4. Interfejs (na sztywno do współrzędnych ekranu) ---
        self.radar_obj.draw(window, self.player, self.enemy_manager, self.asteroid_manager, dt)
        self.game_controller.draw(window)