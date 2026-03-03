import pygame
import os

class MusicManager():
    def __init__(self, audio_files: list | tuple):
        self.audio_files = audio_files
        # pre_init z małym buforem eliminuje opóźnienia (lag) dźwięku
        # pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        # Zwiększamy limit głosów, aby przy dużej zadymie dźwięki nie znikały
        pygame.mixer.set_num_channels(128)
        
        # Cache dźwięków - ładujemy raz do pamięci RAM
        self.sounds = {}
        for path in audio_files:
            if os.path.exists(path):
                self.sounds[path] = pygame.mixer.Sound(path)

        # Muzyka tła
        if os.path.exists("./data/images/audio/z_opengameart/WAV/Venus.mp3"):
            pygame.mixer.music.load("./data/images/audio/z_opengameart/WAV/Venus.mp3")
            pygame.mixer.music.set_volume(0.2)
            pygame.mixer.music.play(-1)

    def play(self, path: str, volume: float, sound_is_laser: bool = False):
        sound = self.sounds.get(path)
        if not sound: 
            return

        if sound_is_laser:
            # Ustawiamy głośność dla tego konkretnego odtworzenia
            sound.set_volume(volume)
            
            # KLUCZ: maxtime=200ms. 
            # Nawet jeśli plik trwa 2 sekundy, Pygame wyłączy go po 0.2s.
            # Dzięki temu mikser nie musi przetwarzać setek "ogonów" dźwięku.
            sound.play(maxtime=100) 
        else:
            # Dla wybuchów i innych efektów pozwalamy wybrzmieć normalnie
            sound.set_volume(volume)
            sound.play()

    def at_exit(self):
        pygame.mixer.quit()

    def handle_death(self):
        self.play("./data/images/audio/the_end_1.wav", 0.9, False)