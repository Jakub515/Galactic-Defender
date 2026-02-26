import pygame
import math
import itertools
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from music import MusicManager
    from shoot import Shoot
    from asteroids import AsteroidManager
    from space_ship import SpaceShip, Battle
    from enemy_ship import EnemyManager, Enemy

class Collision():
    def __init__(self, mixer_obj: "MusicManager", cxx: int, cyy: int):
        self.music_obj = mixer_obj
        self._mask_cache = {}
        self.cxx = cxx
        self.cyy = cyy

    def get_masked_data(self, image: pygame.Surface, pos: pygame.math.Vector2, angle: float, obj_id: int):
        """Pobiera maskę. Image musi być obrazkiem bazowym (nieobróconym)."""
        cache_key = (obj_id, int(angle % 360))
        if cache_key in self._mask_cache:
            return self._mask_cache[cache_key]

        rotated_image = pygame.transform.rotate(image, angle)
        rect = rotated_image.get_rect(center=(int(pos.x), int(pos.y)))
        mask = pygame.mask.from_surface(rotated_image)
        
        result = (rect, mask)
        self._mask_cache[cache_key] = result
        return result

    def check_collisions(self, battle: "Battle", player: "SpaceShip", enemy_manager: "EnemyManager", 
                         shoot_obj: "Shoot", asteroid_manager: "AsteroidManager"):
        self._mask_cache = {}
        sw, sh = self.cxx, self.cyy
        player_pos = player.player_pos
        active_dist_sq = (sw * 1.2)**2 

        active_enemies = [e for e in enemy_manager.enemies if not e.is_dead and 
                          (e.pos - player_pos).length_squared() < active_dist_sq]
        active_asteroids = [a for a in asteroid_manager.asteroids if 
                            (a.pos - player_pos).length_squared() < active_dist_sq]

        for shot in shoot_obj.shots[:]:
            if shot.get("is_exploding"): continue
            shot_pos = shot["pos"]
            shot_hit = False
            
            # 1. Kolizja z asteroidami (zawsze niszczy pocisk)
            for asteroid in active_asteroids:
                if (shot_pos - asteroid.pos).length_squared() < asteroid.radius**2:
                    shot_hit = True
                    break
            if shot_hit: 
                self._process_shot_impact(shot, shoot_obj)
                continue

            # 2. Kolizja z graczem (tylko pociski wrogów)
            if shot.get("is_enemy_shot"):
                if (shot_pos - player_pos).length_squared() < 35**2:
                    shot_hit = True
                    if not battle.shield_active: 
                        player.hp -= shot["damage"]
                    else:
                        if not player.is_destroyed:
                            self.music_obj.play("images/audio/kenney_sci-fi-sounds/forceField_001.wav", 0.25)
                    if player.hp <= 0: return True # Game Over

            if shot_hit: 
                self._process_shot_impact(shot, shoot_obj)
                continue

            # 3. Kolizja z wrogami
            for enemy in active_enemies:
                # Gracz może trafić każdego wroga. 
                # Wróg może trafić innego wroga (ale nie samego siebie).
                is_own_shot = shot.get("is_enemy_shot") and shot.get("enemy_id") == enemy.id
                
                if not is_own_shot:
                    if (shot_pos - enemy.pos).length_squared() < 55**2:
                        enemy.hp -= shot["damage"]
                        shot_hit = True
                        if enemy.hp <= 0:
                            enemy.death()
                        break # Trafił jednego, przerywamy pętlę wrogów

            if shot_hit: 
                self._process_shot_impact(shot, shoot_obj)
                continue

        # --- 3. KOLIZJE STATKÓW ---
        
        # Gracz vs Asteroidy
        for asteroid in active_asteroids:
            if (player_pos - asteroid.pos).length_squared() < (40 + asteroid.radius)**2:
                r1, m1 = self.get_masked_data(player.actual_frame, player_pos, player.angle, id(player))
                r2, m2 = self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))
                if m1.overlap(m2, (r2.left - r1.left, r2.top - r1.top)):
                    self._handle_asteroid_impact(player, asteroid, damage=15)
                    if player.hp <= 0: return True

        # Wrogowie vs Asteroidy
        for enemy in active_enemies:
            # POBIERANIE OBRAZKA Z MANAGERA (Naprawa błędu Image)
            enemy_base_img = enemy_manager.ship_base_images[enemy.type_name]
            
            for asteroid in active_asteroids:
                if (enemy.pos - asteroid.pos).length_squared() < (45 + asteroid.radius)**2:
                    r1, m1 = self.get_masked_data(enemy_base_img, enemy.pos, enemy.angle, id(enemy))
                    r2, m2 = self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))
                    if m1.overlap(m2, (r2.left - r1.left, r2.top - r1.top)):
                        self._handle_asteroid_impact(enemy, asteroid, damage=30)
                        if enemy.hp <= 0: enemy.death()
                        break

        # Gracz -> Wróg
        if not player.is_destroyed:
            for enemy in active_enemies:
                if (player_pos - enemy.pos).length_squared() < 95**2:
                    enemy_base_img = enemy_manager.ship_base_images[enemy.type_name]
                    r1, m1 = self.get_masked_data(player.actual_frame, player_pos, player.angle, id(player))
                    r2, m2 = self.get_masked_data(enemy_base_img, enemy.pos, enemy.angle, id(enemy))
                    if m1.overlap(m2, (r2.left - r1.left, r2.top - r1.top)):
                        self._handle_ship_collision(player, enemy)
                        if enemy.hp <= 0: enemy.death()

        # Wróg -> Wróg
        for e1, e2 in itertools.combinations(active_enemies, 2):
            if (e1.pos - e2.pos).length_squared() < 85**2:
                img1 = enemy_manager.ship_base_images[e1.type_name]
                img2 = enemy_manager.ship_base_images[e2.type_name]
                r1, m1 = self.get_masked_data(img1, e1.pos, e1.angle, id(e1))
                r2, m2 = self.get_masked_data(img2, e2.pos, e2.angle, id(e2))
                if m1.overlap(m2, (r2.left - r1.left, r2.top - r1.top)):
                    self._handle_enemy_to_enemy_collision(e1, e2)
                    if e1.hp <= 0: e1.death()
                    if e2.hp <= 0: e2.death()
        
        return False

    def _process_shot_impact(self, shot, shoot_obj):
        if shot.get("rocket"):
            shot["is_exploding"] = True
            shot["vel"] *= 0.05
        else:
            if shot in shoot_obj.shots:
                shoot_obj.shots.remove(shot)

    def _handle_enemy_to_enemy_collision(self, e1, e2):
        push_dir = (e1.pos - e2.pos)
        if push_dir.length_squared() > 0: push_dir = push_dir.normalize()
        else: push_dir = pygame.math.Vector2(1, 0)
        e1.pos += push_dir * 8
        e2.pos -= push_dir * 8
        e1.velocity *= -0.4
        e2.velocity *= -0.4
        e1.hp = 0
        e2.hp = 0

    def _handle_asteroid_impact(self, ship, asteroid, damage: int):
        is_player = hasattr(ship, 'player_pos')
        ship_pos = ship.player_pos if is_player else ship.pos
        push_dir = ship_pos - asteroid.pos
        if push_dir.length_squared() > 0: push_dir = push_dir.normalize()
        else: push_dir = pygame.math.Vector2(1, 0)
        
        if is_player:
            ship.hp = 0
            ship.destroy_cause_collision()
        else:
            ship.pos += push_dir * 12
            ship.hp = 0
        ship.velocity *= -0.5

    def _handle_ship_collision(self, player, enemy):
        push_dir = (player.player_pos - enemy.pos)
        if push_dir.length_squared() > 0: push_dir = push_dir.normalize()
        else: push_dir = pygame.math.Vector2(1, 0)
        player.player_pos += push_dir * 20
        player.velocity *= -0.5
        player.hp = 0
        enemy.hp = 0
        player.destroy_cause_collision()