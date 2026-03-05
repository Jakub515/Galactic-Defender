import pygame
import utils.load_images as load_images
import utils.music as music
import core.event as event
import core.sky as sky
from core.game_manager import Game  

# A. Inicjalizacja
pygame.init()

info = pygame.display.Info()

width = info.current_w
height = info.current_h

window = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
cxx, cyy = window.get_size()
clock = pygame.time.Clock()

# B. Zasoby
image_loader = load_images.ImageLoad()
gfx_40, gfx_100, audio = image_loader.load_all_assets()
music_obj = music.MusicManager(audio)
events_obj = event.Event()
bg = sky.SpaceBackground(cxx, cyy, cxx, cyy, 50)

def main():
    game_obj = Game(cxx, cyy, gfx_40, gfx_100, audio, music_obj, events_obj, clock)
    running = True
    while running:
        dt = clock.tick(60) / 1000.0 
        events_obj.update()
        if events_obj.system_exit:
            running = False

        # Logika i rysowanie
        game_obj.mainloop(dt)
        if hasattr(game_obj, "camera"):
            bg.draw(window, (game_obj.camera.pos.x, game_obj.camera.pos.y))
        
        game_obj.draw(window, dt)
        pygame.display.flip()

    music_obj.at_exit()
    pygame.quit()

if __name__ == "__main__":
    main()