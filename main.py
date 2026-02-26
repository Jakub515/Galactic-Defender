import pygame
import load_images
import space_ship
from sky import SpaceBackground

pygame.init()

clock = pygame.time.Clock()

window = pygame.display.set_mode((1920,1080), pygame.FULLSCREEN)
pygame.display.set_caption("Kosmos")

image_load = load_images.ImageLoad()

space_frames = ["images/space_ships/playerShip1_blue.png","images/space_ships/playerShip1_green.png","images/space_ships/playerShip1_orange.png","images/space_ships/playerShip1_red.png","images/space_ships/playerShip2_blue.png","images/space_ships/playerShip2_green.png","images/space_ships/playerShip2_orange.png","images/space_ships/playerShip2_red.png","images/space_ships/playerShip3_blue.png","images/space_ships/playerShip3_green.png","images/space_ships/playerShip3_orange.png","images/space_ships/playerShip3_red.png","images/space_ships/spaceShips_001.png","images/space_ships/spaceShips_002.png","images/space_ships/spaceShips_003.png","images/space_ships/spaceShips_004.png","images/space_ships/spaceShips_005.png","images/space_ships/spaceShips_006.png","images/space_ships/spaceShips_007.png","images/space_ships/spaceShips_008.png","images/space_ships/spaceShips_009.png","images/space_ships/ufoBlue.png","images/space_ships/ufoGreen.png","images/space_ships/ufoRed.png","images/space_ships/ufoYellow.png"]
space_parts = []
audio_files = []

loaded_space_frames = []
for i in space_frames:
    loaded_space_frames.append(image_load.get_image(i,100))

player = space_ship.SpaceShip(loaded_space_frames,space_parts,audio_files,1920,1080)

running = True

scroll_up = False
scroll_down = False

WORLD_SIZE = 5000000 # To jest tylko logiczna granica, nie fizyczna powierzchnia
TILE_WIDTH = 1920
TILE_HEIGHT = 1080

#bg = SpaceBackground(width=100000, height=100000, screen_width=1920, screen_height=1080,num_stars=10000)
bg = SpaceBackground(tile_width=TILE_WIDTH, tile_height=TILE_HEIGHT, screen_width=1920, screen_height=1080, num_stars=100)
player_pos = [WORLD_SIZE // 2, WORLD_SIZE // 2] # Utrzymaj gracza w środku logicznego świata
player_pos = [5000,5000]

clock = pygame.time.Clock()
FPS = 60

moving_left = moving_right = moving_up = moving_down = False
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                moving_left = True
            elif event.key == pygame.K_RIGHT:
                moving_right = True
            elif event.key == pygame.K_UP:
                moving_up = True
            elif event.key == pygame.K_DOWN:
                moving_down = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                moving_left = False
            elif event.key == pygame.K_RIGHT:
                moving_right = False
            elif event.key == pygame.K_UP:
                moving_up = False
            elif event.key == pygame.K_DOWN:
                moving_down = False

    # Aktualizacja pozycji gracza
    if moving_left:
        player_pos[0] -= 5
    if moving_right:
        player_pos[0] += 5
    if moving_up:
        player_pos[1] -= 5
    if moving_down:
        player_pos[1] += 5
    
    bg.draw(window, player_pos)
    player.draw(window)

    pygame.display.flip()

    clock.tick(FPS)

pygame.quit()