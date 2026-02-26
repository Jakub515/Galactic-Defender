import pygame
import load_images
import space_ship
from sky import SpaceBackground
import enemy_ship
import time
import os
from collections import defaultdict
from functions import Event

pygame.init()
pygame.mixer.init()

clock = pygame.time.Clock()

window = pygame.display.set_mode((1920,1080), pygame.FULLSCREEN)
pygame.display.set_caption("Kosmos")

image_load = load_images.ImageLoad()

base_folder = os.path.join(os.getcwd(), "images")
if not os.path.exists(base_folder):
    print("Folder 'images' nie istnieje.")
else:
    files_by_ext = defaultdict(list)

    # Rekurencyjne przeszukiwanie folderu
    for root, _, files in os.walk(base_folder):
        for file in files:
            _, ext = os.path.splitext(file)
            ext = ext.lower() or "<bez rozszerzenia>"

            # Pełna ścieżka względna względem katalogu roboczego
            rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
            rel_path = rel_path.replace("\\", "/")  # 👈 zamiana backslashy
            files_by_ext[ext].append(rel_path)


    # Posortowany wynik
    space_frames = []
    audio_files = []
    for ext in sorted(files_by_ext):
        print(f"\nRozszerzenie: {ext}")
        for path in sorted(files_by_ext[ext]):
            print(f"  {path}")
            if ext == ".png":
                space_frames.append(path)
            if ext == ".wav":
                audio_files.append(path)

space_parts = []

loaded_space_frames = {}

for path in space_frames:
    loaded_space_frames[path] = image_load.get_image(path, 100)

WORLD_SIZE = 5000000 # To jest tylko logiczna granica, nie fizyczna powierzchnia
TILE_WIDTH = 1920
TILE_HEIGHT = 1080

#bg = SpaceBackground(width=100000, height=100000, screen_width=1920, screen_height=1080,num_stars=10000)
bg = SpaceBackground(tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT, screen_width=1920, screen_height=1080, num_stars=50)
player_pos = [WORLD_SIZE // 2, WORLD_SIZE // 2] # Utrzymaj gracza w środku logicznego świata
player_pos = [5000,5000]

player = space_ship.SpaceShip(loaded_space_frames,space_parts,audio_files,1920,1080, player_pos)

audio_files = []
enemie = enemy_ship.EnemyShip(loaded_space_frames,space_parts,audio_files,1920,1080, player_pos)

running = True

scroll_up = False
scroll_down = False



clock = pygame.time.Clock()
FPS = 60

event = Event()

pygame.mixer.music.load("images/audio/star_wars.mp3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)

while running:
    dt = clock.tick(FPS) / 1000

    event.update()
    if event.system_exit:
        running = False
    if event.click_right:
        print(event.mouse_x,event.mouse_y)

    player_pos = player.update(event.key_up, event.key_down, event.key_right, event.key_left, event.key_space, [event.key_1,event.key_2,event.key_3,event.key_4,event.key_5],dt)
    enemy_update = enemie.update()
    
    bg.draw(window, player_pos)
    player.draw(window)
    enemie.draw(window,player_pos[0],player_pos[1])

    pygame.display.flip()

pygame.mixer.music.stop()
pygame.quit()