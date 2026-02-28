import pygame
import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enemy_ship import EnemyManager, Enemy

class Shoot():
    def __init__(self, images: dict):
        self.images = images
        self.shots = []
        self.explosion_frames = [
            self.images[f"images/dym/Explosion/tile_{str(i).zfill(2)}.png"] for i in range(16)
        ]

    def create_missle(self, data: dict):
        if not isinstance(data.get("vel"), pygame.math.Vector2):
            data["vel"] = pygame.math.Vector2(data.get("vel", (0, 0)))
        
        data["spawn_time"] = time.time()
        data["is_exploding"] = False
        data["frame_index"] = 0
        
        if "max-speed" not in data:
            data["max-speed"] = data["vel"].length() if data["vel"].length() > 0 else 12
            
        self.shots.append(data)

    def update(self, enemy_manager: "EnemyManager"):
        current_time = time.time()
        
        for shot in self.shots[:]:
            # --- 1. OBSŁUGA EKSPLOZJI ---
            if shot["is_exploding"]:
                shot["frame_index"] += 0.5
                if shot["frame_index"] >= len(self.explosion_frames):
                    if shot in self.shots:
                        self.shots.remove(shot)
                continue

            # --- 2. LOGIKA CZASU ŻYCIA ---
            time_alive = current_time - shot["spawn_time"]
            if time_alive > shot.get("time-alive-all"):
                if shot.get("rocket"):
                    shot["is_exploding"] = True
                else:
                    self.shots.remove(shot)
                continue

            # --- 3. LOGIKA RAKIET (TYLKO DLA RAKIET) ---
            if shot.get("rocket"):
                max_speed = shot.get("max-speed")
                target_id = shot.get("destination")
                
                # Naprowadzanie (arming delay 0.4s)
                if shot.get("is_enemy_shot"):
                    if time_alive > shot.get("time-alive_before_manewring"):
                        player = target_id
                    
                        target_pos = pygame.math.Vector2(player.player_pos)
                        desired = (target_pos - shot["pos"])
                        
                        if desired.length_squared() > 0:
                            desired = desired.normalize() * max_speed
                            steer = desired - shot["vel"]
                            
                            # Czułość skrętu
                            steer_limit = shot.get("steer-limit")
                            if steer.length() > steer_limit:
                                steer.scale_to_length(steer_limit)
                            
                            shot["vel"] += steer

                elif shot.get("is_player_shooting"):
                    if target_id is not None and time_alive > shot.get("time-alive_before_manewring"):
                        enemy = enemy_manager.get_enemy_by_id(target_id)
                        
                        if enemy and not enemy.is_dead:
                            target_pos = pygame.math.Vector2(enemy.pos)
                            desired = (target_pos - shot["pos"])
                            
                            if desired.length_squared() > 0:
                                desired = desired.normalize() * max_speed
                                steer = desired - shot["vel"]
                                
                                # Czułość skrętu
                                steer_limit = shot.get("steer-limit")
                                if steer.length() > steer_limit:
                                    steer.scale_to_length(steer_limit)
                                
                                shot["vel"] += steer

                # Wymuszenie stałej prędkości tylko dla rakiet (lasery mają stałą z definicji)
                if shot["vel"].length() != 0:
                    shot["vel"].scale_to_length(max_speed)
                
                # Aktualizacja kąta obrotu grafiki rakiety
                shot["dir"] = math.degrees(math.atan2(-shot["vel"].y, shot["vel"].x))

            # --- 4. RUCH WSPÓLNY ---
            shot["pos"] += shot["vel"]

        if len(self.shots) > 100:
            self.shots.pop(0)

    def draw(self, window: pygame.Surface, offset_x: float, offset_y: float):
        for shot in self.shots:
            s_x = shot["pos"].x - offset_x
            s_y = shot["pos"].y - offset_y
            
            if not (-100 < s_x < window.get_width() + 100 and -100 < s_y < window.get_height() + 100):
                continue

            if not shot["is_exploding"]:
                # Obrót o -90 dla poprawnego wyrównania grafiki
                rotated_img = pygame.transform.rotate(shot["img"], shot["dir"] - 90)
                rect = rotated_img.get_rect(center=(int(s_x), int(s_y)))
                window.blit(rotated_img, rect)
            else:
                idx = int(shot["frame_index"])
                if idx < len(self.explosion_frames):
                    frame = self.explosion_frames[idx]
                    rect = frame.get_rect(center=(int(s_x), int(s_y)))
                    window.blit(frame, rect)