import threading
from queue import Queue

class LoadingManager:
    def __init__(self, screen_width: int, screen_height: int):
        self.cxx = screen_width
        self.cyy = screen_height
        self.loading_queue = Queue()
        self.is_loading = False
        self.loading_status = "INITIALIZING..."

    def start_async_load(self, task_func, *args, status_text="LOADING..."):
        """Uruchamia proces ładowania w tle, przekazując wszystkie argumenty."""
        self.is_loading = True
        self.loading_status = status_text
        
        # Kluczowa zmiana: Zawsze przekazujemy args do wątku. 
        # Jeśli args jest puste, Python przekaże pustą krotkę poprawnie.
        thread = threading.Thread(
            target=task_func, 
            args=args, 
            daemon=True
        )
        thread.start()

    def check_finished(self) -> bool:
        """Sprawdza kolejkę w poszukiwaniu sygnału 'DONE'."""
        try:
            # Używamy get_nowait(), aby nie blokować głównej pętli gry
            msg = self.loading_queue.get_nowait()
            if msg == "DONE":
                self.is_loading = False
                return True
        except:
            pass
        return False