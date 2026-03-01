import pygame
import load_images, space_ship, collisions, music, shoot, radar, ui, level_manager
from sky import SpaceBackground
from event import Event
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
pygame.display.set_caption("Galaxy Defender")

# --- B. ŁADOWANIE ZASOBÓW (Zintegrowane w module) ---
image_loader = load_images.ImageLoad()
# Wszystko dzieje się teraz w jednej linijce
loaded_space_frames, loaded_space_frames_full, audio_files = image_loader.load_all_assets()

# --- C. TWORZENIE OBIEKTÓW ---
music_obj = music.MusicManager(audio_files)
events_obj = Event()
bg = SpaceBackground(cxx, cyy, cxx, cyy, 50)

class Game():
    def __init__(self):
        self.WORLD_CENTER = pygame.math.Vector2(0, 0)
        self.WORLD_RADIUS = 25_000
        self.FADE_ZONE = 2000
        self.shoot_obj = shoot.Shoot(loaded_space_frames)
        self.camera = Camera(cxx, cyy, lerp_factor=0.08, offset_scalar=15)
        self.player_parameters = space_ship.Parameters(loaded_space_frames)
        self.player = space_ship.SpaceShip(loaded_space_frames, audio_files, cxx, cyy, [0, 0], music_obj, self.shoot_obj,self.player_parameters)
        self.player_shoot = space_ship.Battle(self.player,loaded_space_frames,audio_files,cxx,cyy,[0,0],music_obj,self.shoot_obj,self.player_parameters)

        self.pola_asteroid = [
            {"pos": pygame.math.Vector2(0, 0), "radius": 22000, "count": 250},
            {"pos": pygame.math.Vector2(0, 0), "radius": 4500, "count": 50}
        ]
        self.asteroid_manager = AsteroidManager(loaded_space_frames_full, self.pola_asteroid)
        self.enemy_manager = EnemyManager(loaded_space_frames, self.player, music_obj, 5, self.shoot_obj, self.WORLD_RADIUS, self.asteroid_manager)

        self.colision_obj = collisions.Collision(music_obj, cxx, cyy, self.enemy_manager)
        self.radar_obj = radar.Radar(cxx, cyy, 200, self.WORLD_RADIUS)
        self.level_manager = level_manager.LevelManager(self.enemy_manager)
        self.game_controller = ui.GameController(self.player_shoot, events_obj, self.player, cxx, cyy, loaded_space_frames_full, clock, self.level_manager, self.colision_obj, self.enemy_manager, self.player_parameters)
        self.level_manager.init_additional_settings(self.game_controller.ui)
        
        self.paused = False
        self.dict = None

    def pause_or_resume(self):
        self.paused = not self.paused

    def mainloop(self, dt:float):
        if self.paused:
            return
        # 2. Logika (Update)
        self.level_manager.update(dt)
        self.game_controller.update(dt)
        self.player.update(dt)
        self.player_shoot.update(dt, self.enemy_manager)
        self.enemy_manager.update(dt)
        self.asteroid_manager.update(dt, self.player, self.enemy_manager)
        self.shoot_obj.update(self.enemy_manager)
        
        # Fizyka bariery świata
        self.dist = self.player.player_pos.distance_to(self.WORLD_CENTER)
        if self.dist > self.WORLD_RADIUS:
            self.player.player_pos = self.WORLD_CENTER + (self.player.player_pos - self.WORLD_CENTER).normalize() * self.WORLD_RADIUS
            self.player.velocity *= -0.3
            self.player.destroy_cause_collision()

        self.colision_obj.check_collisions(self.player_shoot, self.player, self.enemy_manager, self.shoot_obj, self.asteroid_manager, self.level_manager)
        
        # Aktualizacja kamery
        self.camera.update(self.player.player_pos, self.player.velocity)

        # 3. Rysowanie (Draw)
        # Tło pociąga pozycję kamery dla efektu paralaksy/przesuwania

    def draw(self, window: pygame.Surface):
        # Wizualna bariera świata (używamy camera.apply, aby krąg był na właściwych współrzędnych)
        if self.dist > self.WORLD_RADIUS - self.FADE_ZONE:
            alpha = int(max(0, min(1.0, (self.dist - (self.WORLD_RADIUS - self.FADE_ZONE)) / self.FADE_ZONE)) * 255)
            rel_center = self.camera.apply(self.WORLD_CENTER)
            temp_s = pygame.Surface((cxx, cyy), pygame.SRCALPHA)
            pygame.draw.circle(temp_s, (255, 0, 0, alpha // 4), rel_center, self.WORLD_RADIUS, 500)
            pygame.draw.circle(temp_s, (255, 50, 50, alpha), rel_center, self.WORLD_RADIUS, 15)
            window.blit(temp_s, (0, 0))

        # Obiekty świata (używają offsetu kamery)
        off_x, off_y = self.camera.offset.x, self.camera.offset.y
        self.shoot_obj.draw(window, off_x, off_y)
        self.asteroid_manager.draw(window, off_x, off_y, cxx, cyy)
        self.enemy_manager.draw(window, off_x, off_y)
        
        # Gracz (pozycja przeliczona przez kamerę)
        p_draw = self.camera.apply(self.player.player_pos)
        self.player.draw(window, p_draw[0], p_draw[1])
        self.player_shoot.draw(window, p_draw[0], p_draw[1])

        # UI i Radar (na sztywno do ekranu)
        self.radar_obj.draw(window, self.player, self.enemy_manager, self.asteroid_manager, dt)
        self.game_controller.draw(window, dt)


game_obj = Game()

# --- D. GŁÓWNA PĘTLA ---
last_esc_state = False
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    events_obj.update()
    if events_obj.system_exit:
        running = False
    current_esc_state = events_obj.key_escape
    
    if current_esc_state and not last_esc_state:
        game_obj.pause_or_resume()

    if events_obj.key_f5:
        game_obj = Game()
        
    last_esc_state = current_esc_state
    game_obj.mainloop(dt)
    bg.draw(window, (game_obj.camera.pos.x, game_obj.camera.pos.y))
    game_obj.draw(window)
    pygame.display.flip()

# Wyjście
music_obj.at_exit()
pygame.font.quit()
pygame.quit()