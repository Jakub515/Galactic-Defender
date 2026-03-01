import pygame
import os

class ImageLoad:
    def __init__(self):
        """Klasa odpowiedzialna za zarządzanie zasobami graficznymi i dźwiękowymi."""
        pass

    def get_image(self, path: str, scale: int | float | list | tuple):
        """Ładuje i skaluje pojedynczy obraz."""
        try:
            image = pygame.image.load(path)
        except pygame.error as e:
            print(f"Błąd ładowania {path}: {e}")
            return None

        # Optymalizacja formatu pikseli pod pygame-ce
        if image.get_alpha():
            image = image.convert_alpha()
        else:
            image = image.convert()

        # Logika wyliczania skali
        if isinstance(scale, (list, tuple)):
            if len(scale) == 2:
                return pygame.transform.scale(image, (int(scale[0]), int(scale[1])))
            final_scale_value = float(scale[0]) if len(scale) == 1 else 100.0
        else:
            final_scale_value = float(scale)
        
        percent = final_scale_value / 100
        width = int(image.get_width() * percent)
        height = int(image.get_height() * percent)
        return pygame.transform.scale(image, (width, height))

    def load_all_assets(self, base_folder_name="data/images"):
        """
        Skanuje folder ./data/ i ładuje zasoby.
        Dla obrazów tworzy klucze typu 'images/plik.png'.
        Dla dźwięków zwraca pełną ścieżkę względną './data/...'.
        """
        # Standaryzacja ścieżki (np. "data/images")
        base_path = os.path.normpath(base_folder_name)
        # Folder nadrzędny (zazwyczaj "data")
        parent_dir = os.path.dirname(base_path)
        
        image_map = {}
        audio_paths = []

        if not os.path.exists(base_path):
            print(f"Ostrzeżenie: Folder {base_path} nie istnieje!")
            return {}, {}, []

        for root, _, files in os.walk(base_path):
            for file in files:
                # Pełna ścieżka systemowa
                full_path = os.path.normpath(os.path.join(root, file))
                ext = os.path.splitext(file)[1].lower()
                
                if ext in [".png", ".jpg", ".jpeg"]:
                    # Klucz dla obrazów: np. "images/player.png"
                    asset_key = os.path.relpath(full_path, parent_dir).replace("\\", "/")
                    image_map[asset_key] = full_path
                    
                elif ext in [".wav", ".mp3", ".ogg"]:
                    # Ścieżka dla dźwięku: zawsze zaczyna się od "./data/"
                    # relpath od aktualnego katalogu roboczego
                    raw_rel = os.path.relpath(full_path, ".").replace("\\", "/")
                    audio_path = f"./{raw_rel}" 
                    audio_paths.append(audio_path)

        # Generowanie słowników obrazów
        sorted_keys = sorted(image_map.keys())
        gfx_40 = {key: self.get_image(image_map[key], 40) for key in sorted_keys}
        gfx_100 = {key: self.get_image(image_map[key], 100) for key in sorted_keys}

        return gfx_40, gfx_100, sorted(audio_paths)