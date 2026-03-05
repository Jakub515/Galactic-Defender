import pygame
import threading
from queue import Queue

class LoadingManager:
    def __init__(self, screen_width: int, screen_height: int):
        self.cxx = screen_width
        self.cyy = screen_height
        self.loading_queue = Queue()
        self.is_loading = False
        self.loading_status = "INITIALIZING..."
        
        # Inicjalizacja zasobów tekstowych
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 48, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20)

    def start_async_load(self, task_func, *args, flag_load_level_f5=True, status_text="LOADING..."):
        """Uruchamia proces ładowania w tle."""
        self.is_loading = True
        self.loading_status = status_text
        
        # Wybór sposobu przekazania argumentów
        target_args = () if flag_load_level_f5 else args
        
        thread = threading.Thread(target=task_func, args=target_args, daemon=True)
        thread.start()

    def check_finished(self) -> bool:
        """Sprawdza kolejkę w poszukiwaniu sygnału 'DONE'."""
        try:
            msg = self.loading_queue.get_nowait()
            if msg == "DONE":
                self.is_loading = False
                return True
        except:
            pass
        return False

    def draw(self, window: pygame.Surface):
        """Renderuje profesjonalny ekran ładowania."""
        window.fill((5, 5, 15)) # Kosmiczny granat
        
        # Teksty
        load_surf = self.font_large.render("LOADING", True, (255, 255, 255))
        load_rect = load_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 - 40))
        
        status_surf = self.font_small.render(self.loading_status, True, (100, 150, 255))
        status_rect = status_surf.get_rect(center=(self.cxx // 2, self.cyy // 2 + 20))
        
        # Pasek postępu (animowany)
        bar_width = 300
        progress = (pygame.time.get_ticks() / 1000) % 1.0 
        
        # Tło paska
        pygame.draw.rect(window, (30, 30, 50), (self.cxx//2 - bar_width//2, self.cyy//2 + 50, bar_width, 4))
        # Aktywny suwak
        active_w = 60
        pos_x = (self.cxx//2 - bar_width//2) + (bar_width - active_w) * progress
        pygame.draw.rect(window, (0, 200, 255), (pos_x, self.cyy//2 + 50, active_w, 4))

        window.blit(load_surf, load_rect)
        window.blit(status_surf, status_rect)