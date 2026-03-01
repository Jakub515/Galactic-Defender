import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicManager
    from core.level_manager import LevelManager
    from jednostki.shoot import Shoot
    from jednostki.asteroids import AsteroidManager
    from jednostki.space_ship import SpaceShip, Battle
    from src.jednostki.enemy_ship.enemy_ship import EnemyManager

class Collision():
    def __init__(self, mixer_obj: "MusicManager", cxx: int, cyy: int, enemy_manager: "EnemyManager"):
        self.music_obj = mixer_obj
        self._mask_cache = {}
        self.cxx = cxx
        self.cyy = cyy
        self.enemy_manager = enemy_manager

    def get_masked_data(self, image: pygame.Surface, pos: pygame.math.Vector2, angle: float, obj_id: int):
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
                         shoot_obj: "Shoot", asteroid_manager: "AsteroidManager", level_manager: "LevelManager"):
        self._mask_cache = {}  
        player_pos = player.player_pos
        
        # OPTYMALIZACJA 1: Wykorzystanie Rect jako obszaru aktywnego (szybsze niż liczenie pierwiastków)
        active_rect = pygame.Rect(0, 0, self.cxx * 2.2, self.cyy * 2.2)
        active_rect.center = player_pos

        active_enemies = [e for e in enemy_manager.enemies if not e.is_dead and active_rect.collidepoint(e.pos)]
        active_asteroids = [a for a in asteroid_manager.asteroids if active_rect.collidepoint(a.pos)]

        # OPTYMALIZACJA 2: Podział pocisków na grupy (unikamy sprawdzania shot.get w pętlach)
        player_shots = []
        enemy_shots = []
        for s in shoot_obj.shots:
            if s.get("is_exploding"): continue
            if s.get("is_enemy_shot"):
                enemy_shots.append(s)
            else:
                player_shots.append(s)

        def are_colliding(data1, data2):
            r1, m1 = data1
            r2, m2 = data2
            if r1.colliderect(r2):
                return m1.overlap(m2, (r2.left - r1.left, r2.top - r1.top))
            return None

        # --- 1. KOLIZJE POCISKÓW (CCD - Continuous Collision Detection) ---
        
        # A. POCISKI GRACZA -> Wrogowie i Asteroidy
        for shot in player_shots:
            shot_pos = shot["pos"]
            old_pos = shot_pos - shot.get("vel", pygame.math.Vector2(0,0))
            shot_hit = False

            # Vs Asteroidy
            for asteroid in active_asteroids:
                r_ast, _ = self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))
                if r_ast.clipline(old_pos.x, old_pos.y, shot_pos.x, shot_pos.y):
                    shot_hit = True
                    break
            
            # Vs Wrogowie (tylko jeśli nie trafił w asteroidę)
            if not shot_hit:
                for enemy in active_enemies:
                    e_base = enemy_manager.ship_base_images[enemy.type_name]
                    r_en, _ = self.get_masked_data(e_base, enemy.pos, enemy.angle, id(enemy))
                    if r_en.clipline(old_pos.x, old_pos.y, shot_pos.x, shot_pos.y):
                        actual_damage = min(shot["damage"], enemy.hp)
                        level_manager.xp += actual_damage
                        enemy.hp -= shot["damage"]
                        if enemy.hp <= 0: enemy.death()
                        shot_hit = True
                        break

            if shot_hit: self._process_shot_impact(shot, shoot_obj)

        # B. POCISKI WROGÓW -> Gracz i Asteroidy
        for shot in enemy_shots:
            shot_pos = shot["pos"]
            old_pos = shot_pos - shot.get("vel", pygame.math.Vector2(0,0))
            shot_hit = False

            # Vs Asteroidy
            for asteroid in active_asteroids:
                r_ast, _ = self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))
                if r_ast.clipline(old_pos.x, old_pos.y, shot_pos.x, shot_pos.y):
                    shot_hit = True
                    break

            # Vs Gracz
            if not shot_hit:
                r_pl, _ = self.get_masked_data(player.ship_rot, player_pos, player.angle, id(player))
                if r_pl.clipline(old_pos.x, old_pos.y, shot_pos.x, shot_pos.y):
                    if not battle.shield_active:
                        player.hp -= shot["damage"]
                    else:
                        if not player.is_destroyed:
                            self.music_obj.play("./data/images/audio/kenney_sci-fi-sounds/forceField_001.wav", 0.25)
                    shot_hit = True
                    if player.hp <= 0: return True

            if shot_hit: self._process_shot_impact(shot, shoot_obj)

        # --- 2. OBIEKTY FIZYCZNE ---
        p_data = self.get_masked_data(player.ship_rot, player_pos, player.angle, id(player))

        # Gracz vs Asteroidy/Wrogowie
        for asteroid in active_asteroids:
            if (player_pos - asteroid.pos).length_squared() < (45 + asteroid.radius)**2:
                if are_colliding(p_data, self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))):
                    self._handle_asteroid_impact(player, asteroid, 15)
                    if player.hp <= 0: return True

        if not player.is_destroyed:
            for enemy in active_enemies:
                if (player_pos - enemy.pos).length_squared() < 100**2:
                    e_data = self.get_masked_data(enemy_manager.ship_base_images[enemy.type_name], enemy.pos, enemy.angle, id(enemy))
                    if are_colliding(p_data, e_data):
                        self._handle_ship_collision(player, enemy)

        # Wrogowie vs Asteroidy i Inni Wrogowie
        for i, enemy in enumerate(active_enemies):
            e_data = self.get_masked_data(enemy_manager.ship_base_images[enemy.type_name], enemy.pos, enemy.angle, id(enemy))
            
            for asteroid in active_asteroids:
                if (enemy.pos - asteroid.pos).length_squared() < (50 + asteroid.radius)**2:
                    if are_colliding(e_data, self.get_masked_data(asteroid.original_image, asteroid.pos, asteroid.angle, id(asteroid))):
                        self._handle_asteroid_impact(enemy, asteroid, 30)
                        break
            
            for other_enemy in active_enemies[i+1:]:
                if (enemy.pos - other_enemy.pos).length_squared() < 85**2:
                    o_data = self.get_masked_data(enemy_manager.ship_base_images[other_enemy.type_name], other_enemy.pos, other_enemy.angle, id(other_enemy))
                    if are_colliding(e_data, o_data):
                        self._handle_enemy_to_enemy_collision(enemy, other_enemy)
        
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
        push_dir = push_dir.normalize() if push_dir.length_squared() > 0 else pygame.math.Vector2(1, 0)
        e1.pos += push_dir * 10
        e2.pos -= push_dir * 10
        e1.hp = 0
        e2.hp = 0
        e1.death()
        e2.death()

    def _handle_asteroid_impact(self, ship, asteroid, damage: int):
        is_player = hasattr(ship, 'player_pos')
        ship_pos = ship.player_pos if is_player else ship.pos
        
        # 1. Obliczamy wektor od środka asteroidy do statku
        push_dir = (ship_pos - asteroid.pos)
        
        # 2. Normalizacja (nadajemy mu długość 1)
        if push_dir.length_squared() > 0:
            push_dir = push_dir.normalize()
        else:
            push_dir = pygame.math.Vector2(1, 0) # Awaryjny wektor w prawo

        # 3. NADANIE PRĘDKOŚCI (Odrzut)
        # Zmieniamy velocity statku, aby odleciał z dużą siłą
        recoil_strength = 15  # Dostosuj moc odrzutu
        if hasattr(ship, 'velocity'):
            ship.velocity = push_dir * recoil_strength

        # 4. ROZDZIELENIE (Zapobieganie utknięciu w asteroidzie)
        # Przesuwamy statek na krawędź asteroidy + mały margines
        safe_distance = asteroid.radius + 35 
        if is_player:
            ship.player_pos = asteroid.pos + push_dir * safe_distance
            # Pozostała Twoja logika
            ship.hp = 0
            ship.destroy_cause_collision()
        else:
            ship.pos = asteroid.pos + push_dir * safe_distance
            ship.hp = 0
            ship.death()

    def _handle_ship_collision(self, player, enemy):
        # 1. Wektor od wroga do gracza
        push_dir = (player.player_pos - enemy.pos)
        
        if push_dir.length_squared() > 0:
            push_dir = push_dir.normalize()
        else:
            push_dir = pygame.math.Vector2(1, 0)

        # 2. ODRZUT DLA OBU JEDNOSTEK
        force = 15
        if hasattr(player, 'velocity'):
            player.velocity = push_dir * force
        if hasattr(enemy, 'velocity'):
            enemy.velocity = -push_dir * force # Wróg leci w przeciwną stronę

        # 3. ROZDZIELENIE (Przeskok o 20px, by nie nakładały się w klatce wybuchu)
        player.player_pos += push_dir * 20
        
        # Pozostała Twoja logika HP
        player.hp = 0
        enemy.hp = 0
        enemy.death()
        player.destroy_cause_collision()