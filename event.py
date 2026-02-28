import pygame

class Event:
    def __init__(self):
        # OPTYMALIZACJA: Blokowanie zbędnych zdarzeń systemowych (likwiduje lag myszy)
        pygame.event.set_blocked(None)
        pygame.event.set_allowed([
            pygame.QUIT, 
            pygame.KEYDOWN, 
            pygame.KEYUP, 
            pygame.MOUSEBUTTONDOWN, 
            pygame.MOUSEBUTTONUP
        ])

        # --- REKAWICZNA INICJALIZACJA (VS Code widzi te zmienne) ---
        # Sterowanie i specjalne
        self.key_up = self.key_down = self.key_left = self.key_right = False
        self.key_space = self.key_enter = self.key_escape = self.key_delete = False
        self.key_plus = self.key_minus = self.key_tab = self.backquote = False
        self.key_alt_left = self.key_alt_right = self.key_shift_left = False
        self.key_shift_right = self.key_ctrl_left = self.key_ctrl_right = False
        
        self.click_left = self.click_right = False
        self.system_exit = False
        self.mouse_x = self.mouse_y = 0

        # Litery (VS Code teraz będzie podpowiadać key_a, key_b itd.)
        self.key_a = self.key_b = self.key_c = self.key_d = self.key_e = False
        self.key_f = self.key_g = self.key_h = self.key_i = self.key_j = False
        self.key_k = self.key_l = self.key_m = self.key_n = self.key_o = False
        self.key_p = self.key_q = self.key_r = self.key_s = self.key_t = False
        self.key_u = self.key_v = self.key_w = self.key_x = self.key_y = self.key_z = False

        # Cyfry
        self.key_0 = self.key_1 = self.key_2 = self.key_3 = self.key_4 = False
        self.key_5 = self.key_6 = self.key_7 = self.key_8 = self.key_9 = False

        # Klawisze funkcyjne
        self.key_f1 = self.key_f2 = self.key_f3 = self.key_f4 = self.key_f5 = False
        self.key_f6 = self.key_f7 = self.key_f8 = self.key_f9 = self.key_f10 = False
        self.key_f11 = self.key_f12 = False

        # --- MAPOWANIE (Słownik łączący ID klawisza z nazwą zmiennej) ---
        self._key_map = {
            pygame.K_LEFT: "key_left", pygame.K_RIGHT: "key_right",
            pygame.K_UP: "key_up", pygame.K_DOWN: "key_down",
            pygame.K_SPACE: "key_space", pygame.K_RETURN: "key_enter",
            pygame.K_ESCAPE: "key_escape", pygame.K_DELETE: "key_delete",
            pygame.K_TAB: "key_tab", pygame.K_BACKQUOTE: "backquote",
            pygame.K_MINUS: "key_minus", pygame.K_PLUS: "key_plus",
            pygame.K_EQUALS: "key_plus",
            pygame.K_LALT: "key_alt_left", pygame.K_RALT: "key_alt_right",
            pygame.K_LSHIFT: "key_shift_left", pygame.K_RSHIFT: "key_shift_right",
            pygame.K_LCTRL: "key_ctrl_left", pygame.K_RCTRL: "key_ctrl_right",
        }

        # Dynamiczne wypełnienie słownika (oszczędza nam pisania 50 linijek mapowania)
        for c in "abcdefghijklmnopqrstuvwxyz":
            k = getattr(pygame, f"K_{c}", None)
            if k: self._key_map[k] = f"key_{c}"
        for i in range(10):
            k = getattr(pygame, f"K_{i}", None)
            if k: self._key_map[k] = f"key_{i}"
        for i in range(1, 13):
            k = getattr(pygame, f"K_F{i}", None)
            if k: self._key_map[k] = f"key_f{i}"

        # Obsługa strzałek (arrow hold)
        self._arrow_keys = {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN}
        self._arrow_hold = {k: False for k in self._arrow_keys}

    def update(self):
        # Pobieranie pozycji myszy bezpośrednio (zawsze świeże)
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.system_exit = True

            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                state = (event.type == pygame.MOUSEBUTTONDOWN)
                if event.button == 1: self.click_left = state
                elif event.button == 3: self.click_right = state

            elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                state = (event.type == pygame.KEYDOWN)
                
                # Błyskawiczne przypisanie przez słownik
                var_name = self._key_map.get(event.key)
                if var_name:
                    setattr(self, var_name, state)
                
                # Dodatkowa synchronizacja dla strzałek
                if event.key in self._arrow_keys:
                    self._arrow_hold[event.key] = state

        # Finalna aktualizacja strzałek (żeby uniknąć konfliktów KEYUP)
        self.key_left  = self._arrow_hold[pygame.K_LEFT]
        self.key_right = self._arrow_hold[pygame.K_RIGHT]
        self.key_up    = self._arrow_hold[pygame.K_UP]
        self.key_down  = self._arrow_hold[pygame.K_DOWN]