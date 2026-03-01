import pygame

class Camera:
    def __init__(self, screen_width: int, screen_height: int, lerp_factor: float = 0.08, offset_scalar: float = 15):
        self.screen_size = pygame.Vector2(screen_width, screen_height)
        self.half_screen = self.screen_size / 2
        
        # Pozycja kamery w świecie
        self.pos = pygame.Vector2(0, 0)
        
        # Parametry wygładzania i wychylenia
        self.lerp_factor = lerp_factor
        self.offset_scalar = offset_scalar
        
        # Offset używany do rysowania: to co odejmujemy od pozycji obiektów
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_pos: pygame.Vector2, target_velocity: pygame.Vector2):
        """
        target_pos: aktualna pozycja gracza w świecie
        target_velocity: aktualna prędkość gracza (dla efektu wychylenia)
        """
        # 1. Obliczamy punkt, w który kamera "chce" patrzeć
        # Dodajemy wychylenie oparte na prędkości (twój oryginalny pomysł)
        look_at = target_pos + target_velocity * self.offset_scalar
        
        # 2. LERP - płynne przesuwanie pozycji kamery w stronę celu
        self.pos += (look_at - self.pos) * self.lerp_factor
        
        # 3. Obliczamy offset dla renderowania
        # Obiekty rysujemy w: pos_obiektu - pos_kamery + środek_ekranu
        self.offset.x = self.pos.x - self.half_screen.x
        self.offset.y = self.pos.y - self.half_screen.y

    def apply(self, world_pos: pygame.Vector2):
        """Konwertuje pozycję ze świata na pozycję na ekranie."""
        return int(world_pos.x - self.offset.x), int(world_pos.y - self.offset.y)