import pygame
import random

class SpaceBackground:
    # Używamy mniejszych wymiarów dla KAFELKA tła
    def __init__(self, tile_width: int, tile_height: int, screen_width:int, screen_height:int, num_stars:int=500):
        # Wymiary kafelka, który będziemy powtarzać
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Tworzymy powierzchnię kafelka, o rozsądnej wielkości (np. 1920x1080)
        self.tile_surface = pygame.Surface((tile_width, tile_height))
        
        # Losowe tło (czarne z lekkim niebieskim odcieniem)
        base_color = (0, 0, random.randint(10, 30))
        self.tile_surface.fill(base_color)
        
        # Tworzymy gwiazdki na tym kafelku
        for _ in range(num_stars): # 500 gwiazd na kafelek wystarczy
            x = random.randint(0, tile_width - 1)
            y = random.randint(0, tile_height - 1)
            size = random.choice([1, 2, 3])
            color = random.choice([(255,255,255),(255,255,200)])
            pygame.draw.rect(self.tile_surface, color, (x, y, size, size))
    
    def draw(self, screen:pygame.Surface, player_pos: list|tuple):
        px, py = player_pos
        
        # 1. Obliczanie punktu startowego kafelkowania (lewy górny róg widocznego obszaru)
        
        # Środek ekranu to pozycja gracza (px, py).
        # Pozycja lewego górnego rogu ekranu w świecie to (start_x, start_y):
        start_x = int(px - self.screen_width / 2)
        start_y = int(py - self.screen_height / 2)
        
        # 2. Obliczanie, który KAFFELEK zaczyna wypełniać ekran
        
        # Indeks pierwszego kafelka do narysowania:
        first_tile_x = start_x // self.tile_width
        first_tile_y = start_y // self.tile_height
        
        # 3. Obliczanie offsetu (przesunięcia) w pikselach wewnątrz pierwszego kafelka
        
        # Odległość od lewej krawędzi pierwszego kafelka do lewej krawędzi ekranu.
        # Jest to zarazem pozycja kafelka na ekranie (wartość ujemna).
        offset_x = (first_tile_x * self.tile_width) - start_x
        offset_y = (first_tile_y * self.tile_height) - start_y
        
        # 4. Rysowanie kafelek, dopóki nie pokryją całego ekranu
        
        tile_count_x = (self.screen_width // self.tile_width) + 2
        tile_count_y = (self.screen_height // self.tile_height) + 2
        
        for i in range(tile_count_x):
            for j in range(tile_count_y):
                # Pozycja rysowania kafelka na ekranie
                pos_x = offset_x + i * self.tile_width
                pos_y = offset_y + j * self.tile_height
                
                screen.blit(self.tile_surface, (pos_x, pos_y))