from .enemy import Enemy
import json
import pygame
import random
import math

class EnemyManager:
    def __init__(self, ship_frames, player_ref, music_obj, max_enemies, 
                 shoot_obj, world_radius, asteroid_manager):
        self.ship_frames = ship_frames
        self.player_ref = player_ref
        self.music_obj = music_obj
        self.shoot_obj = shoot_obj
        self.max_enemies = max_enemies
        self.world_radius = world_radius
        self.asteroid_manager = asteroid_manager
        self.enemies: list[Enemy] = []
        self.level_transition_active = False  # NOWA FLAGA

        # --- ŁADOWANIE KONFIGURACJI ---
        self.config_all = self._load_config("./data/enemie_slownik.json")
        self.ENEMY_TYPES = self.config_all.get("enemy_types", {})

        # --- CACHE GRAFIKI ---
        self.ship_cache = {}
        self.ship_base_images = {}
        self._init_ship_cache()
        
        self.blue_fire_frames = self._init_fire_frames()
        self.fire_cache = [[] for _ in range(len(self.blue_fire_frames))]
        self._init_fire_cache()

        # --- SYSTEM BRONI (Listy indeksowane) ---
        self.weapons_lasers = []
        self.weapons_rockets = []
        self._init_weapons()

        self.enemy_data_from_level_manager = []
        
        self.can_start_new_level = True # flaga z ui (odnośnie wyboru nagrody)

    def _load_config(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Błąd ładowania JSON: {e}")
            return {}

    def _init_ship_cache(self):
        for name, config in self.ENEMY_TYPES.items():
            path = config.get("image_path")
            if path in self.ship_frames:
                # Rotacja o -90 dla grafik Kenneya
                base_img = pygame.transform.rotate(self.ship_frames[path], -90)
                self.ship_base_images[name] = base_img
                self.ship_cache[name] = [pygame.transform.rotate(base_img, angle) for angle in range(360)]

    def _init_fire_frames(self):
        temp_frames = []
        for i in range(9):
            path = f"images/dym/Explosion/explosion0{i}.png"
            if path in self.ship_frames:
                surf = self.ship_frames[path].copy().convert_alpha()
                for x in range(surf.get_width()):
                    for y in range(surf.get_height()):
                        r, g, b, a = surf.get_at((x, y))
                        if a > 0: surf.set_at((x, y), (b, g, r, a))
                temp_frames.append(pygame.transform.scale(surf, (20, 16)))
        return temp_frames

    def _init_fire_cache(self):
        for i, frame in enumerate(self.blue_fire_frames):
            for angle in range(360):
                self.fire_cache[i].append(pygame.transform.rotate(frame, angle))

    def _init_weapons(self):
        """Wczytuje bronie z 'enemy-weapon-data' do list."""
        w_data = self.config_all.get("enemy-weapon-data", {})
        
        # Lasery
        l_dict = w_data.get("lasers", {})
        # Sortujemy klucze laser1, laser2..., żeby indeksy się zgadzały
        for key in sorted(l_dict.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
            w = l_dict[key]
            img = self.ship_frames.get(w["path"])
            if img:
                self.weapons_lasers.append([img, w["speed"], w["damage"], w["cooldown"], w["time-alive-all"], w["max-speed"]])

        # Rakiety
        # Rakiety
        r_dict = w_data.get("rockets", {})
        for key in sorted(r_dict.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
            w = r_dict[key]
            img = self.ship_frames.get(w["path"])
            if img:
                # Sugerowana nowa kolejność (taka sama jak w Twoim update):
                self.weapons_rockets.append([
                    img,                            # 0
                    w["speed"],                      # 1
                    w["damage"],                     # 2
                    w["cooldown"],                   # 3
                    w["max-speed"],                  # 4
                    w["time-alive_before_manewring"],# 5
                    w["time-alive-all"],             # 6
                    w["steer-limit"]                 # 7
                ])

    def _get_random_weapon(self, bot_config, weapon_key, source_list):
        """Pobiera losową broń na podstawie indeksów z JSON."""
        indices = bot_config.get(weapon_key)
        
        # Jeśli False, None lub pusta lista w JSON
        if indices is False or indices is None or not source_list:
            return None
        
        try:
            # Obsługa listy [1, 2] lub pojedynczej liczby
            chosen_nr = random.choice(indices) if isinstance(indices, list) else indices
            
            # Konwersja na indeks listy (1-based -> 0-based)
            idx = max(0, min(int(chosen_nr) - 1, len(source_list) - 1))
            return source_list[idx]
        except (ValueError, TypeError, IndexError):
            return None
        
    def init_level(self, max_enemy, enemy_data):
        """Wywoływane przy starcie nowego poziomu."""
        self.max_enemies = max_enemy
        self.enemy_data_from_level_manager = enemy_data
        # Wyłączamy blokadę spawnu, bo nowy poziom został zainicjowany
        self.level_transition_active = False 

    def end_level(self):
        """Zamiast blokującej pętli while, tylko flagujemy i uciekamy."""
        self.level_transition_active = True
        for enemy in self.enemies:
            enemy.end_of_level()

    def update(self, dt):
        # 1. Zarządzanie listą przeciwników - usuwanie tych, którzy są martwi lub do skasowania
        # Robimy to na początku, aby operować na aktualnej liście obiektów
        for enemy in self.enemies[:]:
            enemy.update(dt)
            
            # Warunki usunięcia: 
            # - flaga delete_now jest True (wymuszone kasowanie)
            # - LUB jest martwy i skończył animację szczątków/wybuchu
            if enemy.delete_now or (enemy.is_dead and not enemy.debris_list):
                self.enemies.remove(enemy)

        # 2. Logika spawnowania nowych przeciwników
        # Dodajemy warunek: spawnuje TYLKO jeśli nie trwa zmiana poziomu
        if (not self.level_transition_active) and self.can_start_new_level == True:
            living = [e for e in self.enemies if not e.is_dead]
            
            if len(living) < self.max_enemies:
                # Losowanie pozycji spawnu
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(1100, 1500)
                spawn_pos = self.player_ref.player_pos + pygame.math.Vector2(math.cos(angle)*dist, math.sin(angle)*dist)
                
                # Sprawdzamy czy spawn mieści się w świecie i czy mamy dane o przeciwnikach dla tego poziomu
                if spawn_pos.length() < self.world_radius - 300 and self.enemy_data_from_level_manager:
                    
                    # Pobieranie wag prawdopodobieństwa z danych poziomu
                    weights = [e["prawdopodobienstwo"] for e in self.enemy_data_from_level_manager]
                    
                    # 1. Losowanie typu przeciwnika
                    selected_enemy_data = random.choices(self.enemy_data_from_level_manager, weights=weights, k=1)[0]
                    selected_name = selected_enemy_data["type"]
                    
                    # Pobranie konfiguracji bazowej dla tego typu
                    bot_config = self.ENEMY_TYPES.get(selected_name)
                    
                    if bot_config:
                        # --- PRZYGOTOWANIE BRONI ---
                        weapon_data = {
                            "laser": self._get_random_weapon(bot_config, "laser", self.weapons_lasers),
                            "rocket": self._get_random_weapon(bot_config, "rocket", self.weapons_rockets)
                        }
                        
                        # --- TWORZENIE INSTANCJI ---
                        new_enemy = Enemy(
                            selected_name, 
                            bot_config, 
                            self.ship_frames, 
                            self.player_ref, 
                            self.music_obj, 
                            self.shoot_obj, 
                            self, 
                            spawn_pos, 
                            self.asteroid_manager, 
                            self.blue_fire_frames, 
                            weapon_data
                        )
                        self.enemies.append(new_enemy)

    def draw(self, window, camera_x, camera_y):
        for enemy in self.enemies:
            enemy.draw(window, camera_x, camera_y)

    def get_enemy_by_id(self,id) -> Enemy | None:
        for enemy in self.enemies:
            if enemy.id == id:
                return enemy
            
        return None