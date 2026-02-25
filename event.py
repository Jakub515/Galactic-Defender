import pygame

class Event:
    def __init__(self):
        # sterowanie
        self.key_up          = False
        self.key_down        = False
        self.key_left        = False
        self.key_right       = False
        self.key_space       = False
        self.key_alt_left    = False
        self.key_alt_right   = False
        self.key_shift_left  = False
        self.key_shift_right = False
        self.key_ctrl_left   = False
        self.key_ctrl_right  = False
        self.key_enter       = False
        self.key_escape      = False
        self.key_delete      = False
        self.key_plus        = False
        self.key_minus       = False
        self.key_tab         = False
        self.click_left      = False
        self.click_right     = False
        self.system_exit     = False
        self.backquote       = False

        # klawisze funkcyjne
        self.key_f1  = False
        self.key_f2  = False
        self.key_f3  = False
        self.key_f4  = False
        self.key_f5  = False
        self.key_f6  = False
        self.key_f7  = False
        self.key_f8  = False
        self.key_f9  = False
        self.key_f10 = False
        self.key_f11 = False
        self.key_f12 = False

        # cyfry
        self.key_0 = False
        self.key_1 = False
        self.key_2 = False
        self.key_3 = False
        self.key_4 = False
        self.key_5 = False
        self.key_6 = False
        self.key_7 = False
        self.key_8 = False
        self.key_9 = False

        # litery
        self.key_q = False
        self.key_w = False
        self.key_e = False
        self.key_r = False
        self.key_t = False
        self.key_y = False
        self.key_u = False
        self.key_i = False
        self.key_o = False
        self.key_p = False
        self.key_a = False
        self.key_s = False
        self.key_d = False
        self.key_f = False
        self.key_g = False
        self.key_h = False
        self.key_j = False
        self.key_k = False
        self.key_l = False
        self.key_z = False
        self.key_x = False
        self.key_c = False
        self.key_v = False
        self.key_b = False
        self.key_n = False
        self.key_m = False

        self.mouse_x = 0
        self.mouse_y = 0

        # wewnętrzne flagi do utrzymywania stanu strzałek
        self._arrow_hold = {
            pygame.K_LEFT:  False,
            pygame.K_RIGHT: False,
            pygame.K_UP:    False,
            pygame.K_DOWN:  False
        }

    def update(self):
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        # aktualizacja eventów pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.system_exit = True

            # kliknięcia myszy
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.click_left = True
                elif event.button == 3:
                    self.click_right = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.click_left = False
                elif event.button == 3:
                    self.click_right = False

            # klawiatura
            elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                state = (event.type == pygame.KEYDOWN)

                # STRZAŁKI – mają działać ciągle do KEYUP
                if event.key in self._arrow_hold:
                    self._arrow_hold[event.key] = state

                # standardowe przypisanie wszystkich klawiszy
                if event.key == pygame.K_LEFT:
                    self.key_left = state
                elif event.key == pygame.K_RIGHT:
                    self.key_right = state
                elif event.key == pygame.K_UP:
                    self.key_up = state
                elif event.key == pygame.K_DOWN:
                    self.key_down = state

                elif event.key == pygame.K_SPACE:
                    self.key_space = state
                elif event.key == pygame.K_RETURN:
                    self.key_enter = state
                elif event.key == pygame.K_ESCAPE:
                    self.key_escape = state
                elif event.key == pygame.K_DELETE:
                    self.key_delete = state
                elif event.key == pygame.K_TAB:
                    self.key_tab = state
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    self.key_plus = state
                elif event.key == pygame.K_MINUS:
                    self.key_minus = state
                elif event.key == pygame.K_LALT:
                    self.key_alt_left = state
                elif event.key == pygame.K_RALT:
                    self.key_alt_right = state
                elif event.key == pygame.K_LSHIFT:
                    self.key_shift_left = state
                elif event.key == pygame.K_RSHIFT:
                    self.key_shift_right = state
                elif event.key == pygame.K_LCTRL:
                    self.key_ctrl_left = state
                elif event.key == pygame.K_RCTRL:
                    self.key_ctrl_right = state
                elif event.key == pygame.K_BACKQUOTE:
                    self.backquote = state

                # cyfry
                elif event.key == pygame.K_0: self.key_0 = state
                elif event.key == pygame.K_1: self.key_1 = state
                elif event.key == pygame.K_2: self.key_2 = state
                elif event.key == pygame.K_3: self.key_3 = state
                elif event.key == pygame.K_4: self.key_4 = state
                elif event.key == pygame.K_5: self.key_5 = state
                elif event.key == pygame.K_6: self.key_6 = state
                elif event.key == pygame.K_7: self.key_7 = state
                elif event.key == pygame.K_8: self.key_8 = state
                elif event.key == pygame.K_9: self.key_9 = state

                # litery
                elif event.key == pygame.K_q: self.key_q = state
                elif event.key == pygame.K_w: self.key_w = state
                elif event.key == pygame.K_e: self.key_e = state
                elif event.key == pygame.K_r: self.key_r = state
                elif event.key == pygame.K_t: self.key_t = state
                elif event.key == pygame.K_y: self.key_y = state
                elif event.key == pygame.K_u: self.key_u = state
                elif event.key == pygame.K_i: self.key_i = state
                elif event.key == pygame.K_o: self.key_o = state
                elif event.key == pygame.K_p: self.key_p = state
                elif event.key == pygame.K_a: self.key_a = state
                elif event.key == pygame.K_s: self.key_s = state
                elif event.key == pygame.K_d: self.key_d = state
                elif event.key == pygame.K_f: self.key_f = state
                elif event.key == pygame.K_g: self.key_g = state
                elif event.key == pygame.K_h: self.key_h = state
                elif event.key == pygame.K_j: self.key_j = state
                elif event.key == pygame.K_k: self.key_k = state
                elif event.key == pygame.K_l: self.key_l = state
                elif event.key == pygame.K_z: self.key_z = state
                elif event.key == pygame.K_x: self.key_x = state
                elif event.key == pygame.K_c: self.key_c = state
                elif event.key == pygame.K_v: self.key_v = state
                elif event.key == pygame.K_b: self.key_b = state
                elif event.key == pygame.K_n: self.key_n = state
                elif event.key == pygame.K_m: self.key_m = state

                # funkcje
                elif event.key == pygame.K_F1:  self.key_f1 = state
                elif event.key == pygame.K_F2:  self.key_f2 = state
                elif event.key == pygame.K_F3:  self.key_f3 = state
                elif event.key == pygame.K_F4:  self.key_f4 = state
                elif event.key == pygame.K_F5:  self.key_f5 = state
                elif event.key == pygame.K_F6:  self.key_f6 = state
                elif event.key == pygame.K_F7:  self.key_f7 = state
                elif event.key == pygame.K_F8:  self.key_f8 = state
                elif event.key == pygame.K_F9:  self.key_f9 = state
                elif event.key == pygame.K_F10: self.key_f10 = state
                elif event.key == pygame.K_F11: self.key_f11 = state
                elif event.key == pygame.K_F12: self.key_f12 = state

        # po pętli — utrzymanie aktywnych strzałek
        self.key_left  = self._arrow_hold[pygame.K_LEFT]
        self.key_right = self._arrow_hold[pygame.K_RIGHT]
        self.key_up    = self._arrow_hold[pygame.K_UP]
        self.key_down  = self._arrow_hold[pygame.K_DOWN]
