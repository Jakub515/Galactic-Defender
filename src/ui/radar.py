import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jednostki.asteroids import AsteroidManager
    from jednostki.space_ship import SpaceShip
    from jednostki.enemy_ship.enemy_manager import EnemyManager

class Radar:
    def __init__(self, screen_width: int, screen_height: int, radar_size:int=200, world_radius:int=10000, zoom_radius:int=4000):
        self.size = radar_size
        self.world_radius = world_radius
        
        # --- KOLORY ---
        self.border_color = (70, 70, 70)      # Szary kolor obramowania
        self.bg_color = (0, 0, 0, 150)        # Półprzezroczyste czarne tło
        self.player_color = (50, 255, 50)     # Zielony punkt gracza
        self.enemy_color = (255, 50, 50)      # Czerwone punkty wrogów
        self.asteroid_color = (140, 140, 140) # Szare punkty asteroid
        
        # Marginesy i pozycja (Prawy dolny róg)
        self.margin = 20
        self.pos_x = screen_width - self.size - self.margin
        self.pos_y = screen_height - self.size - self.margin
        
        # Powierzchnia maski do przycinania wystających elementów
        self.mask_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(self.mask_surface, (255, 255, 255, 255), (self.size // 2, self.size // 2), self.size // 2)

        # Skalowanie jednostek świata na piksele radaru
        self.zoom_radius = zoom_radius 
        self.scale = self.size / (self.zoom_radius * 2)

        # --- PARAMETRY ANIMACJI ---
        self.pulse_timer = 0.0      
        self.pulse_speed = 0.35     
        self.num_circles = 2        

    def draw(self, window:pygame.Surface, player: "SpaceShip", enemy_manager: "EnemyManager", asteroid_manager: "AsteroidManager", dt: float):
        """
        Renderuje radar, w tym gracza, przeciwników oraz asteroidy.
        """
        # 1. Tworzymy czystą powierzchnię z kanałem Alpha
        temp_radar = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        temp_radar.fill((0, 0, 0, 0))
        
        center = pygame.math.Vector2(self.size // 2, self.size // 2)
        
        # 2. Rysujemy tło radaru (koło)
        pygame.draw.circle(temp_radar, self.bg_color, (int(center.x), int(center.y)), self.size // 2)
        
        # --- LOGIKA PULSOWANIA ---
        self.pulse_timer += self.pulse_speed * dt
        if self.pulse_timer > 1.0:
            self.pulse_timer -= 1.0  
            
        for i in range(self.num_circles):
            offset = i / self.num_circles
            progress = (self.pulse_timer + offset) % 1.0
            current_radius = progress * (self.size // 2)
            alpha = int(160 * (1.0 - progress))
            pygame.draw.circle(temp_radar, (60, 220, 60, alpha), 
                               (int(center.x), int(center.y)), 
                               int(current_radius), 1)

        # --- GRANICA ŚWIATA ---
        rel_world_center = pygame.math.Vector2(0, 0) - player.player_pos
        world_center_radar = center + rel_world_center * self.scale
        world_radar_radius = self.world_radius * self.scale
        
        pygame.draw.circle(temp_radar, (255, 50, 50, 180), 
                           (int(world_center_radar.x), int(world_center_radar.y)), 
                           int(world_radar_radius), 2)

        # --- ASTEROIDY (NOWA SEKCJA) ---
        for asteroid in asteroid_manager.asteroids:
            rel_pos = asteroid.pos - player.player_pos
            # Wyświetlamy tylko obiekty w zasięgu zoomu radaru
            if rel_pos.length() < self.zoom_radius:
                radar_pos = center + rel_pos * self.scale
                # Rysujemy małe kropki dla asteroid
                pygame.draw.circle(temp_radar, self.asteroid_color, (int(radar_pos.x), int(radar_pos.y)), 2)

        # --- WROGOWIE ---
        for enemy in enemy_manager.enemies:
            rel_pos = enemy.pos - player.player_pos
            if rel_pos.length() < self.zoom_radius:
                radar_pos = center + rel_pos * self.scale
                pygame.draw.circle(temp_radar, self.enemy_color, (int(radar_pos.x), int(radar_pos.y)), 3)

        # --- GRACZ I JEGO KIERUNEK ---
        direction_vec = pygame.math.Vector2(7, 0).rotate(-player.angle)
        pygame.draw.line(temp_radar, (255, 255, 255), 
                         (int(center.x), int(center.y)), 
                         (int(center.x + direction_vec.x), int(center.y + direction_vec.y)), 2)

        pygame.draw.circle(temp_radar, self.player_color, (int(center.x), int(center.y)), 4)

        # --- MASKOWANIE I FINALIZACJA ---
        temp_radar.blit(self.mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        window.blit(temp_radar, (self.pos_x, self.pos_y))
        
        # Stała obwódka zewnętrzna
        pygame.draw.circle(window, self.border_color, 
                           (int(self.pos_x + center.x), int(self.pos_y + center.y)), 
                           self.size // 2, 2)