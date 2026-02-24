import pygame
import math
import itertools  # Dodane do wydajnego sprawdzania par
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicManager
    from shoot import Shoot
    from asteroids import AsteroidManager
    from space_ship import SpaceShip, Battle
    from enemy_ship import EnemyManager, Enemy

class Collision():
    def __init__(self, mixer_obj: "MusicManager"):
        self.music_obj = mixer_obj
        
    def get_masked_data(self, image: pygame.Surface, pos:pygame.math.Vector2, angle: float):
        rotated_image = pygame.transform.rotate(image, angle)
        rect = rotated_image.get_rect(center=(pos.x, pos.y))
        mask = pygame.mask.from_surface(rotated_image)
        return rect, mask

    def check_mask_collision(self, obj1_img:pygame.Surface, obj1_pos:pygame.math.Vector2, obj1_angle: float, obj2_img:pygame.Surface, obj2_pos:pygame.math.Vector2, obj2_angle:float):
        rect1, mask1 = self.get_masked_data(obj1_img, obj1_pos, obj1_angle)
        rect2, mask2 = self.get_masked_data(obj2_img, obj2_pos, obj2_angle)

        offset_x = rect2.left - rect1.left
        offset_y = rect2.top - rect1.top

        return mask1.overlap(mask2, (offset_x, offset_y))

    def check_collisions(self, battle: "Battle", player: "SpaceShip", enemy_manager: "EnemyManager", shoot_obj: "Shoot", asteroid_manager: "AsteroidManager"):
        # --- 1. KOLIZJE POCISKÓW ---
        for shot in shoot_obj.shots[:]:
            if shot.get("is_exploding"):
                continue

            shot_hit = False
            
            for asteroid in asteroid_manager.asteroids:
                dist_sq = (shot["pos"] - asteroid.pos).length_squared()
                if dist_sq < asteroid.radius**2:
                    shot_hit = True
                    break

            if not shot_hit:
                if not shot.get("is_enemy_shot", False):
                    for enemy in enemy_manager.enemies[:]:
                        if getattr(enemy, 'is_dead', False):
                            continue
                            
                        dist_sq = (shot["pos"] - enemy.pos).length_squared()
                        if dist_sq < 60**2:
                            enemy.hp -= shot["damage"]
                            shot_hit = True
                            if enemy.hp <= 0:
                                enemy.death()
                            break 
                else:
                    dist_sq = (shot["pos"] - player.player_pos).length_squared()
                    if dist_sq < 35**2:
                        shot_hit = True
                        if not battle.shield_active:
                            player.hp -= shot["damage"]
                        else:
                            self.music_obj.play("images/audio/kenney_sci-fi-sounds/forceField_001.wav", 0.25)
                        
                        if player.hp <= 0:
                            return True

            if shot_hit:
                if shot.get("rocket"):
                    shot["is_exploding"] = True
                    shot["vel"] *= 0.05
                else:
                    if shot in shoot_obj.shots:
                        shoot_obj.shots.remove(shot)

        # --- 2. KOLIZJE STATKÓW Z ASTEROIDAMI ---
        # Gracz vs Asteroidy
        for asteroid in asteroid_manager.asteroids:
            dist_sq = (player.player_pos - asteroid.pos).length_squared()
            if dist_sq < (35 + asteroid.radius)**2:
                hit = self.check_mask_collision(
                    player.actual_frame, player.player_pos, player.angle,
                    asteroid.original_image, asteroid.pos, asteroid.angle
                )
                if hit:
                    self._handle_asteroid_impact(player, asteroid, damage=10)
                    if player.hp <= 0: return True

        # Wrogowie vs Asteroidy
        for enemy in enemy_manager.enemies:
            if getattr(enemy, 'is_dead', False): continue

            for asteroid in asteroid_manager.asteroids:
                dist_sq = (enemy.pos - asteroid.pos).length_squared()
                if dist_sq < (40 + asteroid.radius)**2:
                    hit = self.check_mask_collision(
                        enemy.image, enemy.pos, enemy.angle,
                        asteroid.original_image, asteroid.pos, asteroid.angle
                    )
                    if hit:
                        self._handle_asteroid_impact(enemy, asteroid, damage=20)
                        if enemy.hp <= 0:
                            enemy.death()
                        break

        # --- 3. KOLIZJA: GRACZ -> WRÓG ---
        for enemy in enemy_manager.enemies:
            if getattr(enemy, 'is_dead', False) or getattr(player, 'is_destroyed', True):
                continue

            dist_sq = (player.player_pos - enemy.pos).length_squared()
            if dist_sq < 90**2:
                hit = self.check_mask_collision(
                    player.actual_frame, player.player_pos, player.angle,
                    enemy.image, enemy.pos, enemy.angle
                )
                if hit:
                    self._handle_ship_collision(player, enemy)
                    if enemy.hp <= 0:
                        enemy.death()

        # --- 4. KOLIZJA: WRÓG -> WRÓG (NOWE) ---
        # itertools.combinations bierze każdą parę wrogów tylko raz
        for enemy1, enemy2 in itertools.combinations(enemy_manager.enemies, 2):
            if enemy1.is_dead or enemy2.is_dead:
                continue

            dist_sq = (enemy1.pos - enemy2.pos).length_squared()
            # Sprawdzamy kolizję tylko jeśli są blisko siebie (optymalizacja)
            if dist_sq < 80**2:
                hit = self.check_mask_collision(
                    enemy1.image, enemy1.pos, enemy1.angle,
                    enemy2.image, enemy2.pos, enemy2.angle
                )
                if hit:
                    self._handle_enemy_to_enemy_collision(enemy1, enemy2)
                    if enemy1.hp <= 0: enemy1.death()
                    if enemy2.hp <= 0: enemy2.death()
        
        return False

    def _handle_enemy_to_enemy_collision(self, e1, e2):
        """Logika zderzenia dwóch wrogów."""
        push_dir = (e1.pos - e2.pos)
        if push_dir.length() > 0:
            push_dir = push_dir.normalize()
        else:
            push_dir = pygame.math.Vector2(1, 0)
        
        # Rozpychamy ich od siebie
        e1.pos += push_dir * 10
        e2.pos -= push_dir * 10
        
        # Odbicie prędkości
        e1.velocity *= -0.5
        e2.velocity *= -0.5
        
        # Obrażenia przy zderzeniu
        e1.hp -= 20
        e2.hp -= 20

    def _handle_asteroid_impact(self, ship, asteroid, damage: int):
        ship_pos = ship.player_pos if hasattr(ship, 'player_pos') else ship.pos
        push_dir = ship_pos - asteroid.pos
        push_dir = push_dir.normalize() if push_dir.length() > 0 else pygame.math.Vector2(1, 0)
            
        if hasattr(ship, 'player_pos'): # Gracz
            ship.player_pos += push_dir * 15
            ship.hp -= damage
            ship.destroy_cause_collision()
        else: # Wróg
            ship.pos += push_dir * 15
            ship.hp -= damage
            
        ship.velocity *= -0.5

    def _handle_ship_collision(self, player, enemy):
        push_dir = (player.player_pos - enemy.pos)
        push_dir = push_dir.normalize() if push_dir.length() > 0 else pygame.math.Vector2(1, 0)
        player.player_pos += push_dir * 20
        player.velocity *= -0.5
        player.hp -= 20
        enemy.hp -= 100
        player.destroy_cause_collision()