import json
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jednostki.enemy_ship.enemy_manager import EnemyManager
    from ui.ui import UI
    
class LevelManager():
    def __init__(self, enemy_manager: "EnemyManager") -> None:
        self.enemy_manager = enemy_manager

        self.level = 1
        self.xp = 0

        self.json_config = self._load_json()
        self.load_new_level(self.level)

    def init_additional_settings(self, ui: "UI"):
        self.ui = ui

    def load_new_level(self, level: int) -> list:
        self.enemy_manager.end_level()
        level_data = self.json_config.get(f"level_{level}", {})
        if level_data == {}:
            print("Nie ma leveli do załadowania")
            exit(404)
            
        word_data = level_data.get("world_config", {})
        
        self.word_radius = word_data.get("word_radius", 1000)
        asteroid_data = word_data.get("asteroid_data", {})
        
        self.asteroid_data = []
        for i in asteroid_data:
            self.asteroid_data.append({"pos": pygame.math.Vector2(i["center_x"], i["center_y"]), "radius": i["radius"], "count": i["count"]})
        
        self.max_enemy = level_data.get("max-enemy", 0)
        self.max_xp = level_data.get("max-xp", 1)
        self.enemy_data = level_data.get("enemy-data", {})
        self.rewards = level_data.get("rewards", {})
        
        self.enemy_manager.world_radius = self.word_radius
        self.enemy_manager.init_level(self.max_enemy, self.enemy_data)
        
        return [self.word_radius, self.asteroid_data]
    
    @staticmethod
    def _load_json() -> dict:
        with open('./data/level_slownik.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def update(self, dt) -> None | list:
        if self.xp >= self.max_xp:
            self.level += 1
            self.enemy_manager.can_start_new_level = False
            ret = self.load_new_level(self.level)
            
            self.ui.rewards_too_choose(self.rewards, dt)
            #self.enemy_manager.can_start_new_level = True
            return ret
            
        return None