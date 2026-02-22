import pygame
import load_images, space_ship, collisions, music, shoot, radar, ui
from sky import SpaceBackground
from functions import Event
from enemy_ship import EnemyManager
from asteroids import AsteroidManager
from camera import Camera

# --- A. INICJALIZACJA I KONFIGURACJA ---
pygame.init()
pygame.font.init()

FPS = 60
clock = pygame.time.Clock()
window = pygame.display.set_mode((1920, 1080 ), pygame.FULLSCREEN)
cxx, cyy = window.get_size()
pygame.display.set_caption("Kosmos")

WORLD_CENTER = pygame.math.Vector2(0, 0)
WORLD_RADIUS = 25_000
FADE_ZONE = 2000

# --- B. ŁADOWANIE ZASOBÓW (Zintegrowane w module) ---
image_loader = load_images.ImageLoad()
# Wszystko dzieje się teraz w jednej linijce
loaded_space_frames, loaded_space_frames_full, audio_files = image_loader.load_all_assets()

# --- C. TWORZENIE OBIEKTÓW ---
music_obj = music.MusicManager(audio_files)
shoot_obj = shoot.Shoot(loaded_space_frames)
events_obj = Event()
camera = Camera(cxx, cyy, lerp_factor=0.08, offset_scalar=15)

bg = SpaceBackground(cxx, cyy, cxx, cyy, 50)
player = space_ship.SpaceShip(loaded_space_frames, audio_files, cxx, cyy, [0, 0], music_obj, shoot_obj)
player_shoot = space_ship.Battle(player,loaded_space_frames,audio_files,cxx,cyy,[0,0],music_obj,shoot_obj)

pola_asteroid = [
    {"pos": pygame.math.Vector2(0, 0), "radius": 22000, "count": 250},
    {"pos": pygame.math.Vector2(0, 0), "radius": 4500, "count": 50}
]
asteroid_manager = AsteroidManager(loaded_space_frames_full, pola_asteroid)
enemy_manager = EnemyManager(loaded_space_frames, player, music_obj, 20, shoot_obj, WORLD_RADIUS, asteroid_manager)

colision_obj = collisions.Collision(music_obj)
radar_obj = radar.Radar(cxx, cyy, 200, WORLD_RADIUS)
game_controller = ui.GameController(player_shoot, events_obj, player, cxx, cyy, loaded_space_frames_full, clock)

# --- D. GŁÓWNA PĘTLA ---
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # 1. Zdarzenia (Input)
    events_obj.update()
    if events_obj.key_escape or events_obj.system_exit:
        running = False

    # 2. Logika (Update)
    game_controller.update(dt)
    player.update(dt)
    player_shoot.update(dt)
    enemy_manager.update(dt)
    asteroid_manager.update(dt, player, enemy_manager)
    shoot_obj.update()
    
    # Fizyka bariery świata
    dist = player.player_pos.distance_to(WORLD_CENTER)
    if dist > WORLD_RADIUS:
        player.player_pos = WORLD_CENTER + (player.player_pos - WORLD_CENTER).normalize() * WORLD_RADIUS
        player.velocity *= -0.3
        player.destroy_cause_collision()

    colision_obj.check_collisions(player_shoot, player, enemy_manager, shoot_obj, asteroid_manager)
    
    # Aktualizacja kamery
    camera.update(player.player_pos, player.velocity)

    # 3. Rysowanie (Draw)
    # Tło pociąga pozycję kamery dla efektu paralaksy/przesuwania
    bg.draw(window, (camera.pos.x, camera.pos.y))

    # Wizualna bariera świata (używamy camera.apply, aby krąg był na właściwych współrzędnych)
    if dist > WORLD_RADIUS - FADE_ZONE:
        alpha = int(max(0, min(1.0, (dist - (WORLD_RADIUS - FADE_ZONE)) / FADE_ZONE)) * 255)
        rel_center = camera.apply(WORLD_CENTER)
        temp_s = pygame.Surface((cxx, cyy), pygame.SRCALPHA)
        pygame.draw.circle(temp_s, (255, 0, 0, alpha // 4), rel_center, WORLD_RADIUS, 500)
        pygame.draw.circle(temp_s, (255, 50, 50, alpha), rel_center, WORLD_RADIUS, 15)
        window.blit(temp_s, (0, 0))

    # Obiekty świata (używają offsetu kamery)
    off_x, off_y = camera.offset.x, camera.offset.y
    shoot_obj.draw(window, off_x, off_y)
    asteroid_manager.draw(window, off_x, off_y)
    enemy_manager.draw(window, off_x, off_y)
    
    # Gracz (pozycja przeliczona przez kamerę)
    p_draw = camera.apply(player.player_pos)
    player.draw(window, p_draw[0], p_draw[1])
    player_shoot.draw(window, p_draw[0], p_draw[1])

    # UI i Radar (na sztywno do ekranu)
    radar_obj.draw(window, player, enemy_manager, asteroid_manager, dt)
    game_controller.draw(window)

    pygame.display.flip()

# Wyjście
music_obj.at_exit()
pygame.font.quit()
pygame.quit()