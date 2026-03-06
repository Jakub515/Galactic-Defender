import json

class Parameters:
    def __init__(self, ship_frames):
        # --- STATYSTYKI ŻYCIA ---
        self.hp = 1000
        self.max_hp = 1000
        self.hp_reg_speed = 1

        # --- FIZYKA I PRĘDKOŚĆ ---
        self.max_speed = 10.0
        self.boost_speed = 22.0
        self.thrust_power = 0.4
        self.braking_force = 0.92
        self.linear_friction = 0.985
        self.idle_friction = 0.985

        self.max_switch_time = 2.5 # czas przełączenia między laserami a rakietami
        
        # --- TARCZA (OSŁONY) ---
        self.shield_max_timer = 250      # Czas trwania w klatkach
        self.max_shield_cooldown = 1.0   # Czas odnowienia w sekundach
        
        # --- BOOSTER ---
        self.max_boost_cooldown = 50.0   # Pojemność paska
        self.boost_drain_rate = 1.5      # Szybkość zużycia (dt * x)
        self.boost_regen_rate = 0.8      # Szybkość regeneracji (dt * x)

        self.weapons = []
        self.weapons_2 = []
        self._load_weapons_from_config("./data/player_slownik.json", ship_frames) #

    def add_idle_friction(self, amount: float | int) -> None:
        # Pamiętaj, że "zmniejszenie tarcia" to zbliżanie się do 1.0
        self.idle_friction += amount
        
    def add_weapons_1_speed(self, speed: float | int) -> None:
        for i in range(len(self.weapons)):
            self.weapons[i][4] += speed
            # struktura: [img, w["speed"], w["damage"], w["cooldown"], w["max-speed"], w["time-alive-all"]]
    
    def add_weapons_1_damage(self, damage: float | int) -> None:
        for i in range(len(self.weapons)):
            self.weapons[i][2] += damage
    
    def reduce_weapons_1_reload(self, reload: float | int) -> None:
        for i in range(len(self.weapons)):
            self.weapons[i][3] -= reload
    
    def add_weapons_2_speed(self, speed: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][1] += speed
        # struktura: [img, w["speed"], w["damage"], w["cooldown"], w["max-speed"],
        #   "time-alive_before_manewring"], w["time-alive-all"], w["steer-limit"]]
    
    def add_weapons_2_max_speed(self, max_speed: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][4] += max_speed
    
    def add_weapons_2_damage(self, damage: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][2] += damage
    
    def reduce_weapons_2_reload(self, reload: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][3] -= reload
    
    def add_weapons_2_time_alive(self, time_alive: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][6] += time_alive
    
    def add_weapons_2_steer_limit(self, steer_limit: float | int) -> None:
        for i in range(len(self.weapons_2)):
            self.weapons_2[i][7] += steer_limit
        
    def reduce_max_switch_time(self, max_switch_time: float | int) -> None:
        self.max_switch_time -= max_switch_time
        
    def reduce_max_shield_cooldown(self, max_shield_cooldown: float | int) -> None:
        self.max_shield_cooldown += max_shield_cooldown
        
    def add_shield_max_timer(self, shield_max_timer: float | int) -> None:
        self.shield_max_timer += shield_max_timer
        
    def reduce_linear_friction(self, linear_friction: float | int) -> None:
        self.linear_friction -= linear_friction
        
    def add_braking_force(self,braking_force: float | int) -> None:
        self.braking_force += braking_force
        
    def add_max_boost_cooldown(self, max_boost_cooldown: float | int) -> None:
        self.max_boost_cooldown += max_boost_cooldown
        
    def add_hp_reg_speed(self, hp_reg_speed: float | int) -> None:
        self.hp_reg_speed += hp_reg_speed

    def add_max_hp(self, max_hp: float | int) -> None:
        self.max_hp += max_hp

    def add_max_speed(self, max_speed: float | int) -> None:
        self.max_speed += max_speed
        
    def add_boost_speed(self, boost_speed: float | int) -> None:
        self.boost_speed += boost_speed
        
    def add_thrust_power(self, thrust_power: float | int) -> None:
        self.thrust_power += thrust_power
        
    def _load_weapons_from_config(self, filename: str, ship_frames: dict):
        """Wczytuje definicje broni z sekcji player-weapon-data pliku JSON."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f) #
            
            weapon_data = config.get("player-weapon-data", {}) #

            # Wczytywanie laserów (Set 1)
            lasers = weapon_data.get("lasers", {}) #
            for key in sorted(lasers.keys(), key=lambda x: int(x.replace('laser', ''))): #
                w = lasers[key]
                img = ship_frames.get(w["path"]) #
                if img:
                    self.weapons.append([img, w["speed"], w["damage"], w["cooldown"], w["max-speed"], w["time-alive-all"]]) #

            # Wczytywanie rakiet (Set 2)
            rockets = weapon_data.get("rockets", {}) #
            for key in sorted(rockets.keys(), key=lambda x: int(x.replace('rocket', ''))): #
                w = rockets[key]
                img = ship_frames.get(w["path"]) #
                if img:
                    self.weapons_2.append([img, w["speed"], w["damage"], w["cooldown"], w["max-speed"],
                                           w["time-alive_before_manewring"], w["time-alive-all"], w["steer-limit"]]) #

        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Exception(f"Błąd ładowania broni gracza: {e}") from e
        
