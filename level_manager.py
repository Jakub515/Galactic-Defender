class LevelManager():
    def __init__(self):
        self.xp = 0
        self.max_xp_list = [100,1000,10_000]
        self.count = 0
        self.level = 1
        self.max_xp = self.max_xp_list[self.count]

    def update(self):
        if self.xp >= self.max_xp:
            self.count += 1
            self.level += 1
            self.max_xp = self.max_xp_list[self.count]