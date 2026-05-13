# MIT License - Copyright (c) 2026 XiaxiaStudioGames (XSGames)
import pygame
import random
import math
import json
import os
import sys

pygame.init()
try:
    pygame.key.stop_text_input()
except Exception:
    pass

# Block IME composition events (Chinese IME fix)
try:
    pygame.event.set_blocked(pygame.TEXTEDITING)
except Exception:
    pass
try:
    pygame.event.set_blocked(pygame.TEXTINPUT)
except Exception:
    pass
try:
    pygame.mixer.init()
except Exception:
    pass

WIDTH, HEIGHT = 480, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("打飞机 - 星际猎手")

# Icon
icon = pygame.Surface((32, 32), pygame.SRCALPHA)
# Body
for y in range(4, 28):
    hw = max(1, int((y - 4) * 0.3))
    for x in range(16 - hw, 16 + hw + 1):
        icon.set_at((x, y), (40, 200, 180))
# Nose
for y in range(0, 6):
    w = max(1, y)
    for x in range(16 - w, 16 + w + 1):
        icon.set_at((x, y), (80, 240, 220))
# Cockpit
for y in range(6, 12):
    w = max(1, (12 - y) // 2)
    for x in range(16 - w, 16 + w + 1):
        icon.set_at((x, y), (200, 255, 255))
# Left wing
for y in range(12, 26):
    w = max(2, (y - 12) * 2)
    for x in range(16 - w, 16 - w + 4):
        icon.set_at((x, y), (20, 150, 130))
# Right wing
for y in range(12, 26):
    w = max(2, (y - 12) * 2)
    for x in range(16 + w - 4, 16 + w):
        icon.set_at((x, y), (20, 150, 130))
# Engine glow
for y in range(26, 30):
    c = 255 - (y - 26) * 30
    for x in range(13, 15):
        icon.set_at((x, y), (c, c // 3, 0))
    for x in range(17, 19):
        icon.set_at((x, y), (c, c // 3, 0))
# Wing tips
icon.set_at((0, 20), (80, 200, 180))
icon.set_at((1, 19), (80, 200, 180))
icon.set_at((31, 20), (80, 200, 180))
icon.set_at((30, 19), (80, 200, 180))
pygame.display.set_icon(icon)

clock = pygame.time.Clock()

HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.json")
_total_time_import = 0
LOG_FILE = os.path.join(os.path.dirname(__file__), "game.log")

_log_buf = []
_log_frame = [0]

def _log(msg):
    _log_buf.append(f"[F{_log_frame[0]:04d}] {msg}")
    if len(_log_buf) >= 50:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(_log_buf) + "\n")
        _log_buf.clear()

def _log_flush():
    if _log_buf:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(_log_buf) + "\n")
        _log_buf.clear()

def _key_name(k):
    d = {pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT",
         pygame.K_w: "W", pygame.K_s: "S", pygame.K_a: "A", pygame.K_d: "D",
         pygame.K_SPACE: "SPACE", pygame.K_RETURN: "ENTER", pygame.K_e: "E", pygame.K_k: "K"}
    return d.get(k, f"key_{k}")

_log_frame[0] = 0
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("=== GAME LOG ===\n")

# ---- Colors ----
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 230, 80)
RED = (240, 40, 60)
YELLOW = (255, 220, 30)
ORANGE = (255, 140, 20)
BLUE = (40, 140, 255)
PURPLE = (180, 40, 255)
CYAN = (0, 230, 230)
GRAY = (60, 60, 80)
DARK = (20, 20, 35)

# ---- Fonts ----
font_small = pygame.font.SysFont("simhei", 20)
font = pygame.font.SysFont("simhei", 28)
font_big = pygame.font.SysFont("simhei", 52)
font_title = pygame.font.SysFont("simhei", 64)

# ---- Sounds ----
SOUND_VOLUME = [1.0]

def play_sound(snd):
    try:
        if snd:
            snd.set_volume(SOUND_VOLUME[0])
            snd.play()
    except Exception:
        pass

try:
    sample_rate = pygame.mixer.get_init()[0] if pygame.mixer.get_init() else 22050

    def make_sound(freq, duration, vol=0.3):
        n_samples = int(sample_rate * duration)
        arr = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            val = int(vol * 16000 * math.sin(2 * math.pi * freq * t) * max(0, 1 - t / duration))
            val = max(-32767, min(32767, val))
            arr.extend([val & 0xFF, (val >> 8) & 0xFF])
        return pygame.mixer.Sound(buffer=bytes(arr))

    snd_shoot = make_sound(880, 0.08, 0.15)
    snd_hit = make_sound(220, 0.15, 0.3)
    snd_explode = make_sound(80, 0.4, 0.4)
    snd_powerup = make_sound(660, 0.2, 0.25)
    snd_boss = make_sound(150, 0.5, 0.3)
    snd_life = make_sound(440, 0.3, 0.3)
except Exception:
    snd_shoot = snd_hit = snd_explode = snd_powerup = snd_boss = snd_life = None

# ---- Sprite Factory ----
def _px(surf, x, y, color):
    """Set a pixel (safe)."""
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)

def _fill_rect(surf, x, y, w, h, color):
    for dy in range(h):
        for dx in range(w):
            _px(surf, x + dx, y + dy, color)

def _draw_line(surf, x1, y1, x2, y2, color):
    pygame.draw.line(surf, color, (x1, y1), (x2, y2))

def make_player_sprite():
    s = pygame.Surface((36, 48), pygame.SRCALPHA)
    # Main body - dark gray
    for y in range(6, 44):
        half = int((y - 6) * 0.35)
        for x in range(18 - half, 18 + half):
            _px(s, x, y, (40, 180, 80))
    # Nose tip
    for y in range(0, 8):
        w = max(1, y // 2)
        for x in range(18 - w, 18 + w + 1):
            _px(s, x, y, (60, 220, 100))
    # Cockpit
    for y in range(10, 20):
        w = max(1, (20 - y) // 2)
        for x in range(18 - w, 18 + w + 1):
            _px(s, x, y, (100, 255, 220))
    # Left wing
    for y in range(18, 36):
        wing = int((y - 18) * 0.7) + 6
        for x in range(max(0, 18 - wing), 18 - y//4):
            c = 60 if y < 30 else 30
            _px(s, x, y, (c, 180 - (y-18), c))
    # Right wing
    for y in range(18, 36):
        wing = int((y - 18) * 0.7) + 6
        for x in range(18 + y//4, min(36, 18 + wing)):
            c = 60 if y < 30 else 30
            _px(s, x, y, (c, 180 - (y-18), c))
    # Left engine
    for y in range(38, 46):
        for x in range(12, 16):
            _px(s, x, y, (80, 80, 90))
    # Right engine
    for y in range(38, 46):
        for x in range(21, 25):
            _px(s, x, y, (80, 80, 90))
    # Engine glow (left)
    for y in range(44, 48):
        for x in range(12, 16):
            _px(s, x, y, (200, 100, 0))
    # Engine glow (right)
    for y in range(44, 48):
        for x in range(21, 25):
            _px(s, x, y, (200, 100, 0))
    # Wing tips
    _px(s, 0, 30, (30, 120, 30))
    _px(s, 1, 29, (30, 120, 30))
    _px(s, 1, 31, (30, 120, 30))
    _px(s, 35, 30, (30, 120, 30))
    _px(s, 34, 29, (30, 120, 30))
    _px(s, 34, 31, (30, 120, 30))
    return s

def make_scout_sprite():
    s = pygame.Surface((28, 28), pygame.SRCALPHA)
    c = (160, 210, 255)
    # Body ellipse
    for y in range(4, 24):
        half = int(((y-4) * 0.35) * (1 - abs(y-14)/12))
        for x in range(14 - half, 14 + half):
            _px(s, x, y, c)
    # Dome
    for y in range(2, 8):
        half = max(1, int((8-y) * 0.6))
        for x in range(14 - half, 14 + half + 1):
            _px(s, x, y, (100, 200, 255))
    # Antenna
    _px(s, 14, 0, (255, 100, 100))
    _px(s, 14, 1, (255, 100, 100))
    # Lights
    colors = [(255, 200, 50), (255, 50, 50), (50, 255, 50)]
    for i, col in enumerate(colors):
        _px(s, 7 + i*7, 20, col)
        _px(s, 7 + i*7, 21, col)
    # Center eye
    _px(s, 14, 14, (255, 50, 50))
    _px(s, 13, 14, (255, 50, 50))
    _px(s, 14, 13, (255, 50, 50))
    _px(s, 15, 14, (255, 50, 50))
    _px(s, 14, 15, (255, 50, 50))
    return s

def make_fighter_sprite():
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    # Main body
    for y in range(6, 36):
        half = int((y - 6) * 0.3)
        for x in range(20 - half, 20 + half):
            _px(s, x, y, (200, 50, 70))
    # Nose
    for y in range(0, 8):
        w = max(1, y // 3)
        for x in range(20 - w, 20 + w + 1):
            _px(s, x, y, (230, 80, 100))
    # Forward-swept wings
    for y in range(18, 34):
        wing = int((y - 18) * 0.5) + 6
        for x in range(max(0, 20 - wing), 20 - (34-y)//3):
            _px(s, x, y, (160, 30, 50))
        for x in range(20 + (34-y)//3, min(40, 20 + wing)):
            _px(s, x, y, (160, 30, 50))
    # Cockpit
    for y in range(8, 16):
        w = max(1, (16 - y) // 2)
        for x in range(20 - w, 20 + w + 1):
            _px(s, x, y, (255, 200, 100))
    # Engines
    for x in range(16, 19):
        _px(s, x, 35, (100, 100, 110))
        _px(s, x, 36, (100, 100, 110))
        _px(s, x, 37, (200, 100, 0))
    for x in range(22, 25):
        _px(s, x, 35, (100, 100, 110))
        _px(s, x, 36, (100, 100, 110))
        _px(s, x, 37, (200, 100, 0))
    # Wing cannons
    _px(s, 6, 22, (80, 80, 80))
    _px(s, 6, 23, (80, 80, 80))
    _px(s, 33, 22, (80, 80, 80))
    _px(s, 33, 23, (80, 80, 80))
    return s

def make_bomber_sprite():
    s = pygame.Surface((52, 44), pygame.SRCALPHA)
    c = (120, 30, 160)
    # Wide body
    for y in range(6, 40):
        half = int((y - 6) * 0.4) + 4
        for x in range(26 - half, 26 + half):
            _px(s, x, y, c)
    # Front armor
    for y in range(2, 8):
        w = max(2, y)
        for x in range(26 - w, 26 + w):
            _px(s, x, y, (150, 50, 190))
    # Side wings
    for y in range(14, 36):
        wing = int((y - 14) * 0.6) + 4
        for x in range(max(0, 26 - wing), 26 - wing//2):
            _px(s, x, y, (90, 20, 130))
        for x in range(26 + wing//2, min(52, 26 + wing)):
            _px(s, x, y, (90, 20, 130))
    # Cockpit
    for y in range(8, 14):
        w = max(1, (14 - y) // 2)
        for x in range(26 - w, 26 + w + 1):
            _px(s, x, y, (255, 100, 200))
    # Engines
    for dx in [-10, 10]:
        for y in range(38, 44):
            for x in range(26 + dx - 3, 26 + dx + 3):
                _px(s, x, y, (60, 60, 70))
            for x in range(26 + dx - 2, 26 + dx + 2):
                _px(s, x, 43, (200, 80, 0))
                _px(s, x, 42, (200, 80, 0))
    # Bomb bay detail
    for x in range(22, 31):
        _px(s, x, 28, (60, 15, 90))
    # Wing lights
    _px(s, 2, 18, (255, 255, 50))
    _px(s, 2, 19, (255, 255, 50))
    _px(s, 49, 18, (255, 255, 50))
    _px(s, 49, 19, (255, 255, 50))
    return s

def make_boss_sprite():
    s = pygame.Surface((80, 60), pygame.SRCALPHA)
    # Massive hull
    for y in range(8, 56):
        half = int((y - 8) * 0.35) + 8
        for x in range(40 - half, 40 + half):
            _px(s, x, y, (160, 20, 20))
    # Front wedge
    for y in range(0, 10):
        w = max(2, int(y * 0.6))
        for x in range(40 - w, 40 + w + 1):
            _px(s, x, y, (200, 40, 40))
    # Side armor plates
    for y in range(10, 52):
        plate_w = int((y - 10) * 0.5) + 16
        for x in range(max(0, 40 - plate_w), 40 - plate_w + 4):
            _px(s, x, y, (120, 10, 10))
        for x in range(40 + plate_w - 4, min(80, 40 + plate_w)):
            _px(s, x, y, (120, 10, 10))
    # Central command tower
    for y in range(4, 14):
        w = max(2, 6 - (y - 4) // 2)
        for x in range(40 - w, 40 + w + 1):
            _px(s, x, y, (220, 220, 100))
    # Main gun ports
    for dx in [-20, 0, 20]:
        for y in range(22, 28):
            for x in range(40 + dx - 3, 40 + dx + 3):
                _px(s, x, y, (60, 60, 70))
            _px(s, 40 + dx, 22, (255, 100, 100))
            _px(s, 40 + dx, 23, (255, 100, 100))
    # Engine array
    for dx in [-25, -10, 10, 25]:
        for y in range(54, 60):
            for x in range(40 + dx - 4, 40 + dx + 4):
                _px(s, x, y, (80, 80, 90))
        for x in range(40 + dx - 2, 40 + dx + 2):
            _px(s, x, 59, (255, 120, 0))
            _px(s, x, 58, (255, 120, 0))
    # Shield generators (glowing nodes)
    for dx in [-12, 12]:
        _px(s, 40 + dx, 10, (100, 200, 255))
        _px(s, 40 + dx, 11, (100, 200, 255))
    return s

def make_bullet_sprite():
    s = pygame.Surface((6, 14), pygame.SRCALPHA)
    for y in range(14):
        w = max(1, 3 - abs(y - 7) // 3)
        for x in range(3 - w, 3 + w + 1):
            bright = 255 - y * 8
            _px(s, x, y, (bright, bright, 0))
    # Bright core
    for y in range(3, 11):
        _px(s, 3, y, (255, 255, 255))
    return s

def make_enemy_bullet_sprite():
    s = pygame.Surface((12, 12), pygame.SRCALPHA)
    for r in range(6, 0, -1):
        c = (200 + 55 * (r/6), 30 + 50 * (r/6), 30 + 30 * (r/6))
        pygame.draw.circle(s, c, (6, 6), r)
    _px(s, 6, 6, (255, 255, 200))
    return s

def make_powerup_sprites():
    sprites = {}
    for t, color, symbol in [("spread", ORANGE, "S"), ("rapid", CYAN, "R"), ("shield", BLUE, "H")]:
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (12, 12), 11, 2)
        glow = pygame.Surface((24, 24), pygame.SRCALPHA)
        for r in range(12, 8, -1):
            a = int(60 * (1 - r/12))
            pygame.draw.circle(glow, (*color, a), (12, 12), r)
        s.blit(glow, (0, 0))
        txt = font_small.render(symbol, True, WHITE)
        s.blit(txt, (12 - txt.get_width() // 2, 12 - txt.get_height() // 2))
        sprites[t] = s
    return sprites

def make_life_sprite():
    s = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.polygon(s, RED, [(6, 0), (12, 6), (6, 12), (0, 6)])
    return s

SPRITES = {
    "player": make_player_sprite(),
    "scout": make_scout_sprite(),
    "fighter": make_fighter_sprite(),
    "bomber": make_bomber_sprite(),
    "boss": make_boss_sprite(),
    "bullet": make_bullet_sprite(),
    "enemy_bullet": make_enemy_bullet_sprite(),
    "life": make_life_sprite(),
    "powerup": make_powerup_sprites(),
}

# ---- Helpers ----
def load_highscore():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return json.load(f).get("highscore", 0)
    except: return 0

def save_highscore(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump({"highscore": score}, f)
    except: pass

def export_save(total_time=0, path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "save_backup.json")
    data = {"highscore": load_highscore(), "total_time": total_time}
    try:
        with open(path, "w") as f:
            json.dump(data, f)
        return path
    except:
        return None

def import_save(path=None):
    global _total_time_import
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "save_backup.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        hs = data.get("highscore", 0)
        if hs > load_highscore():
            save_highscore(hs)
        _total_time_import = data.get("total_time", 0)
        return True
    except:
        _total_time_import = 0
        return False

def collide(a, b):
    return a.x < b.x + b.w and a.x + a.w > b.x and a.y < b.y + b.h and a.y + a.h > b.y

# ---- Starfield ----
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.5, 3)
        self.bright = random.randint(100, 255)
        self.r = random.choice([1, 1, 1, 2])

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, s):
        c = (self.bright, self.bright, self.bright)
        pygame.draw.circle(s, c, (int(self.x), int(self.y)), self.r)

stars = [Star() for _ in range(80)]

# ---- Explosion Particles ----
class Particle:
    def __init__(self, x, y, color, count=12):
        self.parts = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 7)
            self.parts.append({
                "x": x, "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.3, 0.8),
                "max_life": random.uniform(0.3, 0.8),
                "color": color,
                "r": random.randint(2, 5),
            })

    def update(self, dt):
        for p in self.parts[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.1
            p["life"] -= dt
            if p["life"] <= 0:
                self.parts.remove(p)

    def draw(self, s):
        for p in self.parts:
            alpha = max(0, int(255 * (p["life"] / p["max_life"])))
            c = tuple(min(255, max(0, v * alpha // 255)) for v in p["color"])
            if alpha > 0:
                pygame.draw.circle(s, c, (int(p["x"]), int(p["y"])), p["r"])

    def done(self):
        return len(self.parts) == 0

# ---- Floating Score Text ----
class FloatingText:
    def __init__(self, x, y, text, color=YELLOW):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 60
        self.vy = -2

    def update(self):
        self.y += self.vy
        self.life -= 1

    def draw(self, s):
        if self.life > 0:
            alpha = min(255, self.life * 5)
            c = tuple(min(v, 255) for v in self.color)
            t = font_small.render(self.text, True, c)
            t.set_alpha(alpha)
            s.blit(t, (self.x - t.get_width() // 2, self.y))

    def done(self):
        return self.life <= 0

# ---- Combo Flash ----
class ScreenFlash:
    def __init__(self, color, duration=15):
        self.color = color
        self.timer = duration
        self.max_timer = duration

    def update(self):
        self.timer -= 1

    def alive(self):
        return self.timer > 0

    def alpha(self):
        return int(120 * self.timer / self.max_timer)

# ---- Power-ups ----
class PowerUp:
    TYPES = ["spread", "rapid", "shield"]
    COLORS = {"spread": ORANGE, "rapid": CYAN, "shield": BLUE}

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 24, 24
        self.type = random.choice(self.TYPES)
        self.speed = 2
        self.t = 0

    def update(self):
        self.y += self.speed
        self.t += 0.05

    def draw(self, s):
        scale = 1 + 0.15 * math.sin(self.t * 3)
        size = int(24 * scale)
        cx, cy = self.x + self.w // 2, self.y + self.h // 2
        sprite = pygame.transform.smoothscale(SPRITES["powerup"][self.type], (size, size))
        s.blit(sprite, (cx - size // 2, cy - size // 2))

# ---- Bullets ----
class Bullet:
    def __init__(self, x, y, vx=0, vy=-10, color=YELLOW, w=4, h=12):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.w, self.h = w, h

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, s):
        s.blit(SPRITES["bullet"], (self.x - 1, self.y))

    def offscreen(self):
        return self.y < -20 or self.y > HEIGHT + 20 or self.x < -20 or self.x > WIDTH + 20

# ---- Enemy Bullet ----
class EnemyBullet:
    def __init__(self, x, y, target_x, target_y):
        self.x, self.y = x, y
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        speed = 5
        self.vx = dx / dist * speed if dist else 0
        self.vy = dy / dist * speed if dist else speed
        self.w, self.h = 8, 8
        self.t = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.t += 0.1

    def draw(self, s):
        scale = 1 + 0.3 * math.sin(self.t * 5)
        size = int(12 * scale)
        sprite = pygame.transform.smoothscale(SPRITES["enemy_bullet"], (size, size))
        s.blit(sprite, (int(self.x) - size // 2, int(self.y) - size // 2))

    def offscreen(self):
        return self.y < -20 or self.y > HEIGHT + 20 or self.x < -20 or self.x > WIDTH + 20

# ---- Enemy classes ----
class EnemyBase:
    def __init__(self):
        self.w = self.h = 36
        self.x = 0
        self.y = -100
        self.speed = 1
        self.hp = 1
        self.max_hp = 1
        self.score_val = 10
        self.shoot_timer = random.randint(60, 180)
        self.flash_timer = 0
        self.drop_rate = 0.08

    def hit(self):
        self.hp -= 1
        self.flash_timer = 5
        return self.hp <= 0

    def update(self):
        self.y += self.speed
        self.shoot_timer -= 1
        if self.flash_timer > 0:
            self.flash_timer -= 1

    def offscreen(self):
        return self.y > HEIGHT + 30

    def draw_hp(self, s):
        if self.max_hp > 1:
            w = self.w
            bar_h = 4
            pygame.draw.rect(s, GRAY, (self.x, self.y - 8, w, bar_h))
            fill = w * self.hp // self.max_hp
            if fill > 0:
                pygame.draw.rect(s, GREEN, (self.x, self.y - 8, fill, bar_h))

class Scout(EnemyBase):
    def __init__(self):
        super().__init__()
        self.w = self.h = 28
        self.speed = random.uniform(2.5, 4)
        self.hp = 1
        self.score_val = 10
        self.x = random.randint(0, WIDTH - self.w)

    def draw(self, s):
        if self.flash_timer > 0:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 160))
            s.blit(flash, (self.x, self.y))
        s.blit(SPRITES["scout"], (self.x, self.y))

class Fighter(EnemyBase):
    def __init__(self):
        super().__init__()
        self.w, self.h = 40, 40
        self.speed = random.uniform(1.5, 2.5)
        self.hp = 2
        self.max_hp = 2
        self.score_val = 25
        self.x = random.randint(0, WIDTH - self.w)
        self.dir = 1

    def update(self):
        super().update()
        self.x += self.dir * 0.8
        if self.x <= 0 or self.x >= WIDTH - self.w:
            self.dir *= -1

    def draw(self, s):
        if self.flash_timer > 0:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 120))
            s.blit(flash, (self.x, self.y))
        s.blit(SPRITES["fighter"], (self.x, self.y))
        self.draw_hp(s)

class Bomber(EnemyBase):
    def __init__(self):
        super().__init__()
        self.w, self.h = 52, 44
        self.speed = random.uniform(1, 1.8)
        self.hp = 4
        self.max_hp = 4
        self.score_val = 50
        self.x = random.randint(0, WIDTH - self.w)
        self.drop_rate = 0

    def update(self):
        super().update()
        self.x += math.sin(self.y * 0.02) * 1.2

    def draw(self, s):
        if self.flash_timer > 0:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 100))
            s.blit(flash, (self.x, self.y))
        s.blit(SPRITES["bomber"], (self.x, self.y))
        self.draw_hp(s)

class Boss(EnemyBase):
    def __init__(self):
        super().__init__()
        self.w, self.h = 80, 60
        self.speed = 0.5
        self.hp = 30
        self.max_hp = 30
        self.score_val = 200
        self.x = WIDTH // 2 - self.w // 2
        self.y = -self.h
        self.dir = 1
        self.drop_rate = 0
        self.phase = 0
        self.phase_timer = 0
        play_sound(snd_boss)

    def update(self):
        if self.y < 60:
            self.y += 1
            return
        super().update()
        self.x += self.dir * 1.5
        if self.x <= 10 or self.x >= WIDTH - self.w - 10:
            self.dir *= -1
        self.phase_timer += 1
        if self.phase_timer > 120:
            self.phase = (self.phase + 1) % 3
            self.phase_timer = 0

    def draw(self, s):
        if self.flash_timer > 0:
            flash = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            flash.fill((255, 100, 100, 100))
            s.blit(flash, (self.x, self.y))
        s.blit(SPRITES["boss"], (self.x, self.y))
        self.draw_hp(s)
        pygame.draw.rect(s, WHITE, (self.x, self.y - 8, self.w, 4))
        hp_ratio = self.hp / self.max_hp
        if hp_ratio > 0:
            pygame.draw.rect(s, RED, (self.x, self.y - 8, int(self.w * hp_ratio), 4))

class BossTank(Boss):
    def __init__(self):
        super().__init__()
        self.hp = 50
        self.max_hp = 50
        self.speed = 0.3
        self.score_val = 300

class BossRapid(Boss):
    def __init__(self):
        super().__init__()
        self.hp = 20
        self.max_hp = 20
        self.speed = 0.8
        self.score_val = 250
        self.phase = 2
        self.phase_timer = -60

BOSS_TYPES = [Boss, BossTank, BossRapid]

# ---- Player ----
PWR_DURATION = 1800  # 30 seconds per stack
PWR_MAX_STACKS = 3

class Player:
    def __init__(self):
        self.w, self.h = 36, 44
        self.x = WIDTH // 2 - self.w // 2
        self.y = HEIGHT - 100
        self.speed = 6
        self.bullets = []
        self.lives = 3
        self.invincible = 0
        self.shoot_cooldown = 0
        self.shoot_delay = 10
        self.power = 0
        self.shield = 0
        self.spread_stacks = []
        self.rapid_stacks = []
        self.shield_stacks = []

    def reset(self):
        self.__init__()

    def _update_stacks(self, stacks, name):
        if not stacks:
            return
        stacks[0] -= 1
        if stacks[0] <= 0:
            stacks.pop(0)
        if name == "spread":
            self.power = len(stacks)
        elif name == "rapid":
            self.shoot_delay = max(4, 10 - len(stacks) * 2)
        elif name == "shield":
            self.shield = len(stacks)

    def add_stack(self, name):
        stacks = getattr(self, f"{name}_stacks")
        stacks.append(PWR_DURATION)
        while len(stacks) > PWR_MAX_STACKS:
            stacks.pop(0)
        if name == "spread":
            self.power = len(stacks)
        elif name == "rapid":
            self.shoot_delay = max(4, 10 - len(stacks) * 2)
        elif name == "shield":
            self.shield = len(stacks)

    def stack_time(self, name):
        stacks = getattr(self, f"{name}_stacks")
        if not stacks:
            return 0
        return sum(stacks) // 60

    def update(self, keys, mx, my, mouse_control):
        if self.invincible > 0:
            self.invincible -= 1

        self._update_stacks(self.spread_stacks, "spread")
        self._update_stacks(self.rapid_stacks, "rapid")
        self._update_stacks(self.shield_stacks, "shield")

        if mouse_control:
            if mx is not None and my is not None:
                target_x = mx - self.w // 2
                target_y = my - self.h // 2
                target_x = max(0, min(WIDTH - self.w, target_x))
                target_y = max(0, min(HEIGHT - self.h, target_y))
                self.x += (target_x - self.x) * 0.15
                self.y += (target_y - self.y) * 0.15
        else:
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
            if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1

            if dx and dy:
                dx *= 0.707
                dy *= 0.707

            self.x += dx * self.speed
            self.y += dy * self.speed
            self.x = max(0, min(WIDTH - self.w, self.x))
            self.y = max(0, min(HEIGHT - self.h, self.y))

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if mouse_control:
            mouse_pressed = pygame.mouse.get_pressed()
            if mouse_pressed[0] and self.shoot_cooldown == 0:
                self.shoot()
                self.shoot_cooldown = self.shoot_delay
        else:
            if keys[pygame.K_SPACE] and self.shoot_cooldown == 0:
                self.shoot()
                self.shoot_cooldown = self.shoot_delay

        for b in self.bullets[:]:
            b.update()
            if b.offscreen():
                self.bullets.remove(b)

    def shoot(self):
        cx = self.x + self.w // 2
        cy = self.y
        if self.power == 0:
            self.bullets.append(Bullet(cx - 2, cy))
        elif self.power == 1:
            self.bullets.append(Bullet(cx - 8, cy, color=CYAN))
            self.bullets.append(Bullet(cx + 4, cy, color=CYAN))
        else:
            self.bullets.append(Bullet(cx - 2, cy, vy=-12))
            self.bullets.append(Bullet(cx - 10, cy, vx=-1.5, vy=-11, color=CYAN))
            self.bullets.append(Bullet(cx + 6, cy, vx=1.5, vy=-11, color=CYAN))
        play_sound(snd_shoot)

    def draw(self, s):
        if self.invincible > 0 and self.invincible % 6 < 3:
            return

        cx, cy = self.x + self.w // 2, self.y + self.h // 2

        # Engine glow animation
        for i in range(2):
            glow = int(120 + 80 * math.sin(pygame.time.get_ticks() * 0.015 + i * 2))
            ox = (i - 0.5) * 10
            pygame.draw.circle(s, (glow, glow // 3, 0), (int(cx + ox), self.y + self.h + 2), 5)
            pygame.draw.circle(s, (glow // 2, glow // 4, 0), (int(cx + ox), self.y + self.h + 2), 8, 1)

        # Sprite
        s.blit(SPRITES["player"], (self.x, self.y))

        # Shield
        if self.shield > 0:
            r = max(self.w, self.h) // 2 + 8
            alpha = int(60 + 50 * math.sin(pygame.time.get_ticks() * 0.006))
            shield_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*BLUE, alpha), (r, r), r, 2)
            pygame.draw.circle(shield_surf, (*CYAN, alpha // 2), (r, r), r - 2, 1)
            s.blit(shield_surf, (cx - r, cy - r))

    def hit(self):
        if self.invincible > 0:
            return False
        if self.shield > 0:
            self.shield_stacks.pop(0)
            self.shield = len(self.shield_stacks)
            self.invincible = 30
            play_sound(snd_hit)
            return False
        self.lives -= 1
        self.invincible = 90
        self.power = max(0, self.power - 1)
        play_sound(snd_explode)
        return self.lives <= 0

    def rect(self):
        return pygame.Rect(self.x + 4, self.y, self.w - 8, self.h)

# ---- Main Game ----
class Game:
    def __init__(self):
        self.state = "menu"
        self.score = 0
        self.highscore = load_highscore()
        self.player = Player()
        self.enemies = []
        self.enemy_bullets = []
        self.powerups = []
        self.particles = []
        self.spawn_timer = 0
        self.difficulty = 1
        self.boss_spawned = False
        self.boss_active = False
        self.combo = 0
        self.combo_timer = 0
        self.screen_shake = 0
        self.tick = 0
        self.gameover_timer = 0
        self.menu_sel = 0
        self.menu_cd = 0
        self.confirm_reset = False
        self.reset_sel = 0
        self.play_time = 0.0
        self.total_time = 0.0
        self._keys_prev = set()
        self._key_down_add = set()
        self.mouse_x = 0
        self.mouse_y = 0
        self.ask_mouse = False
        self.mouse_control = False
        self.ask_mouse_sel = 0
        self.paused = False
        self.pause_sel = 0
        self._esc_pressed = False
        self.input_mode = None
        self.input_text = ""
        self.toast_msg = ""
        self.toast_timer = 0
        self.floats = []
        self.flashes = []
        self.hit_flash = 0
        self.boss_warning = 0
        self.setting_sel = 0
        self.show_settings = False
        self._volume = 10

    def reset(self):
        self.score = 0
        self.player = Player()
        self.enemies.clear()
        self.enemy_bullets.clear()
        self.powerups.clear()
        self.particles.clear()
        self.spawn_timer = 0
        self.difficulty = 1
        self.boss_spawned = False
        self.boss_active = False
        self.combo = 0
        self.combo_timer = 0
        self.screen_shake = 0
        self.gameover_timer = 0
        self.menu_sel = 0
        self.menu_cd = 0
        self.confirm_reset = False
        self.reset_sel = 0
        self.play_time = 0.0
        self._key_down_add = set()
        self._keys_prev = set()
        self.mouse_x = 0
        self.mouse_y = 0
        self.ask_mouse = False
        self.mouse_control = False
        self.ask_mouse_sel = 0
        self.paused = False
        self.pause_sel = 0
        self.input_mode = None
        self.input_text = ""
        self.toast_msg = ""
        self.toast_timer = 0
        self.floats = []
        self.flashes = []
        self.hit_flash = 0
        self.boss_warning = 0

    def spawn_enemy(self):
        r = random.random()
        thresholds = [0.55, 0.85, 0.98]
        if self.difficulty < 3:
            thresholds = [0.7, 0.95, 1.0]

        if r < thresholds[0]:
            self.enemies.append(Scout())
        elif r < thresholds[1]:
            self.enemies.append(Fighter())
        elif r < thresholds[2]:
            self.enemies.append(Bomber())

    def spawn_boss(self):
        self.enemies.append(random.choice(BOSS_TYPES)())
        self.boss_active = True
        self.boss_warning = 0

    def add_explosion(self, x, y, color=ORANGE, count=15):
        self.particles.append(Particle(x, y, color, count))

    def update(self, events):
        self.tick += 1
        if self.toast_timer > 0:
            self.toast_timer -= 1
        esc_now = self._esc_pressed
        self._esc_pressed = False
        self._key_down_add.clear()
        self._keys_prev.clear()

        _log_frame[0] = self.tick

        keys = pygame.key.get_pressed()
        space_pressed = False

        raw = []
        for e in events:
            if e.type == pygame.KEYDOWN:
                raw.append(f"KEYDOWN:{_key_name(e.key)}")
                if e.key == pygame.K_ESCAPE:
                    self._esc_pressed = True
                if self.input_mode:
                    if e.key == pygame.K_RETURN:
                        self._input_confirm()
                    elif e.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif e.key == pygame.K_ESCAPE:
                        self.input_mode = None
                        self.input_text = ""
                        self._esc_pressed = False
                    elif e.unicode and len(self.input_text) < 40:
                        ch = e.unicode
                        if ch.isprintable() and ch not in '\\/:*?"<>|':
                            self.input_text += ch
            elif e.type == pygame.KEYUP:
                raw.append(f"KEYUP:{_key_name(e.key)}")
            elif e.type == pygame.QUIT:
                raw.append("QUIT")
        if raw:
            _log(f"events:{' '.join(raw)}")
        else:
            _log(f"events:none")

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e, pygame.K_k):
                    space_pressed = True
                if e.key in (pygame.K_w, pygame.K_UP):
                    self._key_down_add.add(pygame.K_UP)
                elif e.key in (pygame.K_s, pygame.K_DOWN):
                    self._key_down_add.add(pygame.K_DOWN)
                elif e.key in (pygame.K_a, pygame.K_LEFT):
                    self._key_down_add.add(pygame.K_LEFT)
                elif e.key in (pygame.K_d, pygame.K_RIGHT):
                    self._key_down_add.add(pygame.K_RIGHT)

        _log(f"state={self.state} nav_set={self._key_down_add} space={space_pressed}")
        _log(f"menu_sel={self.menu_sel} confirm={self.confirm_reset} reset_sel={self.reset_sel}")

        if self.state == "menu":
            nav_now = self._key_down_add

            if self.ask_mouse:
                if pygame.K_LEFT in nav_now or pygame.K_a in nav_now:
                    self.ask_mouse_sel = 0
                if pygame.K_RIGHT in nav_now or pygame.K_d in nav_now:
                    self.ask_mouse_sel = 1
                if space_pressed:
                    choice = self.ask_mouse_sel
                    self.ask_mouse = False
                    self.state = "playing"
                    self.reset()
                    self.mouse_control = (choice == 0)
                    pygame.mouse.set_visible(not self.mouse_control)
                    _log(f"ask_mouse: confirm sel={choice} mouse_control={self.mouse_control}")

            elif self.show_settings:
                if pygame.K_LEFT in nav_now:
                    self._volume = max(0, self._volume - 1)
                    SOUND_VOLUME[0] = self._volume / 10
                    _log(f"volume: {self._volume}")
                if pygame.K_RIGHT in nav_now:
                    self._volume = min(10, self._volume + 1)
                    SOUND_VOLUME[0] = self._volume / 10
                    _log(f"volume: {self._volume}")
                if space_pressed:
                    self.show_settings = False

            elif self.confirm_reset:
                if pygame.K_LEFT in nav_now:
                    self.reset_sel = 0
                    _log(f"nav: LEFT -> reset_sel=0")
                if pygame.K_RIGHT in nav_now:
                    self.reset_sel = 1
                    _log(f"nav: RIGHT -> reset_sel=1")
                if space_pressed:
                    _log(f"action: CONFIRM_RESET sel={self.reset_sel}")
                    if self.reset_sel == 0:
                        save_highscore(0)
                        self.highscore = 0
                    self.confirm_reset = False
            else:
                if pygame.K_UP in nav_now:
                    self.menu_sel = (self.menu_sel - 1) % 3
                    _log(f"nav: UP -> menu_sel={self.menu_sel}")
                if pygame.K_DOWN in nav_now:
                    self.menu_sel = (self.menu_sel + 1) % 3
                    _log(f"nav: DOWN -> menu_sel={self.menu_sel}")
                if space_pressed:
                    _log(f"action: SPACE menu_sel={self.menu_sel}")
                    if self.menu_sel == 0:
                        self.ask_mouse = True
                        self.ask_mouse_sel = 0
                    elif self.menu_sel == 1:
                        self.show_settings = True
                    else:
                        self.confirm_reset = True
                        self.reset_sel = 0
                        _log(f" --> confirm_reset=True")

            if self.confirm_reset and esc_now:
                self.confirm_reset = False

            if self.show_settings and esc_now:
                self.show_settings = False

        elif self.state == "playing":
            if esc_now:
                self.paused = not self.paused
                self.pause_sel = 0
                _log(f"--> {'paused' if self.paused else 'unpaused'}")

            if self.paused and not self.input_mode:
                nav = self._key_down_add
                if pygame.K_UP in nav:
                    self.pause_sel = (self.pause_sel - 1) % 5
                if pygame.K_DOWN in nav:
                    self.pause_sel = (self.pause_sel + 1) % 5
                if space_pressed:
                    if self.pause_sel == 0:
                        self.paused = False
                    elif self.pause_sel == 1:
                        self.paused = False
                        self.reset()
                    elif self.pause_sel == 2:
                        self.paused = False
                        self.state = "menu"
                        pygame.mouse.set_visible(True)
                    elif self.pause_sel == 3:
                        self.input_mode = "export"
                        self.input_text = ""
                    elif self.pause_sel == 4:
                        self.input_mode = "import"
                        self.input_text = ""
                        _log(f"input_mode: export")
                    elif self.pause_sel == 3:
                        self.input_mode = "import"
                        self.input_text = ""
                        _log(f"input_mode: import")

            if not self.paused:
                self._game_update(keys)

        elif self.state == "gameover":
            self.gameover_timer -= 1
            if self.gameover_timer <= 0 or (space_pressed and self.gameover_timer < 150):
                _log(f"gameover -> menu (timer={self.gameover_timer})")
                self.state = "menu"
                self.ask_mouse = False
                pygame.mouse.set_visible(True)
                if self.score > self.highscore:
                    self.highscore = self.score
                    save_highscore(self.score)

    def draw(self):
        offset_x = 0
        offset_y = 0
        if self.screen_shake > 0:
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)

        screen.fill(DARK)

        # Stars
        for star in stars:
            star.update()
            star.draw(screen)

        if self.state == "menu":
            self.draw_menu()

        elif self.state == "playing":
            self.draw_game(offset_x, offset_y)
            if self.paused:
                self.draw_pause_menu()

        elif self.state == "gameover":
            self.draw_game(offset_x, offset_y)
            self.draw_overlay()

        if self.toast_timer > 0 and self.state == "playing":
            alpha = min(255, self.toast_timer * 4)
            color = (0, 255, 100) if "成功" in self.toast_msg else (255, 80, 80)
            t = font.render(self.toast_msg, True, color)
            tw = t.get_width()
            pygame.draw.rect(screen, (0, 0, 0, min(160, alpha)), (WIDTH // 2 - tw // 2 - 12, 648, tw + 24, 36), border_radius=6)
            screen.blit(t, (WIDTH // 2 - tw // 2, 654))

        # Screen flashes (combo milestone)
        for f in self.flashes:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((*f.color, f.alpha()))
            screen.blit(overlay, (0, 0))

        # Hit flash (gameplay only, not during gameover)
        if self.hit_flash > 0 and self.state != "gameover":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, self.hit_flash * 8))
            screen.blit(overlay, (0, 0))

        # Last life warning
        if self.state == "playing" and self.player.lives <= 1:
            pulse = int(80 + 60 * math.sin(pygame.time.get_ticks() * 0.008))
            pygame.draw.rect(screen, (255, 0, 0, pulse), (0, 0, WIDTH, 6))
            pygame.draw.rect(screen, (255, 0, 0, pulse), (0, HEIGHT - 6, WIDTH, 6))
            pygame.draw.rect(screen, (255, 0, 0, pulse), (0, 0, 6, HEIGHT))
            pygame.draw.rect(screen, (255, 0, 0, pulse), (WIDTH - 6, 0, 6, HEIGHT))

        # Boss warning
        if self.state == "playing" and self.boss_warning > 0:
            tick = pygame.time.get_ticks()
            sec = max(1, self.boss_warning // 60 + 1)
            pw = 200
            pygame.draw.rect(screen, (40, 0, 0), (WIDTH // 2 - pw // 2, 16, pw, 10), border_radius=5)
            pygame.draw.rect(screen, (255, 60, 60), (WIDTH // 2 - pw // 2, 16, int(pw * self.boss_warning / 80), 10), border_radius=5)
            warn = font_small.render(f"BOSS {sec}s" if sec > 1 else "BOSS!", True, RED if tick % 400 < 200 else YELLOW)
            screen.blit(warn, (WIDTH // 2 - warn.get_width() // 2, 28))

        pygame.display.flip()

    def draw_menu(self):
        tick = pygame.time.get_ticks()

        # BG nebula blobs
        for i, (cx, cy, r, cr, cg, cb) in enumerate([
            (WIDTH // 2, 260, 200, 0, 60, 120),
            (80, 500, 150, 40, 20, 80),
            (WIDTH - 80, 180, 120, 0, 40, 60),
        ]):
            blob = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for j in range(r, -1, -1):
                a = int(12 * (j / r)) if j > r * 0.5 else int(12 * math.sin(j / r * math.pi / 2))
                pygame.draw.circle(blob, (cr, cg, cb, a), (r, r), j)
            screen.blit(blob, (cx - r, cy - r))

        # ---- TOP SECTION: Title ----
        chars = ["飞", "机", "大", "战"]
        gap = 22
        total_w = sum(font_title.render(c, True, BLACK).get_width() for c in chars) + gap * 3
        tx = WIDTH // 2 - total_w // 2
        ty = 70
        cx = tx
        for c in chars:
            ch = font_title.render(c, True, CYAN)
            shadow = font_title.render(c, True, (0, 40, 60))
            screen.blit(shadow, (cx + 3, ty + 3))
            screen.blit(ch, (cx, ty))
            cx += ch.get_width() + gap

        # Pro rainbow
        h = int(tick * 0.2) % 360
        rc = pygame.Color(0)
        rc.hsva = (h, 100, 100, 100)
        pro = font.render("Pro", True, rc)
        screen.blit(pro, (WIDTH // 2 - pro.get_width() // 2, ty + 68))

        # ---- CENTER: Player ship showcase ----
        ship_cx = WIDTH // 2
        ship_cy = 280
        ship_size = 90
        ship_surf = pygame.transform.scale(SPRITES["player"], (ship_size, ship_size))
        ship_copy = ship_surf.copy()
        ship_copy.set_alpha(200)

        # Rotating ring behind ship
        ring_r = ship_size // 2 + 20
        ring_angle = tick * 0.001
        num_dots = 24
        for d in range(num_dots):
            a = ring_angle + d * 2 * math.pi / num_dots
            dx = int(math.cos(a) * ring_r)
            dy = int(math.sin(a) * ring_r)
            dot_alpha = int(80 + 60 * math.sin(tick * 0.003 + d * 0.3))
            pygame.draw.circle(screen, (0, min(255, dot_alpha), min(255, dot_alpha)),
                              (ship_cx + dx, ship_cy + dy), 2)

        # Ship
        wobble = int(4 * math.sin(tick * 0.002))
        screen.blit(ship_copy, (ship_cx - ship_size // 2, ship_cy - ship_size // 2 + wobble))

        # Engine trail particles
        for i in range(3):
            phase = i * 2.1
            px = ship_cx + (i - 1) * 14
            py = ship_cy + ship_size // 2 + 6
            trail = int(4 + 3 * math.sin(tick * 0.015 + phase))
            alpha = int(80 + 60 * abs(math.sin(tick * 0.015 + phase)))
            pygame.draw.circle(screen, (0, alpha, alpha // 3), (px + wobble, py), trail)
            pygame.draw.circle(screen, (0, alpha // 2, alpha // 6), (px + wobble, py + trail + 2), trail // 2)

        # ---- CONTROLS section (subtle, at sides of ship) ----
        for side, scx in [("left", 60), ("right", WIDTH - 60)]:
            for ik, text in enumerate(["WASD", "空格"]):
                t = font_small.render(text, True, (150, 170, 200))
                sy = ship_cy - 20 + ik * 24
                screen.blit(t, (scx - t.get_width() // 2, sy))

        # ---- MENU BUTTONS ----
        btn_y = 400
        btn_icons = [">", "*"]
        btn_labels = ["开 始 游 戏", "设    置", "重 置 数 据"]
        for i in range(3):
            bw, bh = 250, 50
            bx = WIDTH // 2 - bw // 2
            by = btn_y + i * 56

            if i == self.menu_sel:
                # Animated selection background
                pulse = int(3 + 2 * math.sin(tick * 0.006))
                btn_bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
                glow_a = int(40 + 20 * math.sin(tick * 0.005))
                pygame.draw.rect(btn_bg, (0, 180, 220, glow_a), (0, 0, bw, bh), border_radius=8)
                screen.blit(btn_bg, (bx, by))

                # Animated border
                border_a = int(200 + 55 * math.sin(tick * 0.005))
                border_surf = pygame.Surface((bw + pulse * 2, bh + pulse * 2), pygame.SRCALPHA)
                pygame.draw.rect(border_surf, (0, min(255, border_a), min(255, border_a), 255),
                                (0, 0, bw + pulse * 2, bh + pulse * 2), 3, border_radius=10)
                screen.blit(border_surf, (bx - pulse, by - pulse))

                # Arrow indicators (breathing toward button)
                offset = int(14 * abs(math.sin(tick * 0.003)))
                ax = WIDTH // 2 - 160 + offset
                rx = WIDTH // 2 + 160 - offset
                ay = by + bh // 2
                tx = 10
                pygame.draw.polygon(screen, CYAN,
                    [(ax - tx, ay - 7), (ax + tx, ay), (ax - tx, ay + 7)])
                pygame.draw.polygon(screen, CYAN,
                    [(rx + tx, ay - 7), (rx - tx, ay), (rx + tx, ay + 7)])
            else:
                pygame.draw.rect(screen, GRAY, (bx, by, bw, bh), 2, border_radius=8)

            label = font.render(btn_labels[i], True, WHITE if i == self.menu_sel else GRAY)
            screen.blit(label, (WIDTH // 2 - label.get_width() // 2, by + bh // 2 - label.get_height() // 2))

        # ---- STATS (bottom) ----
        stat_y = 560
        # Divider line
        div = pygame.Surface((200, 1), pygame.SRCALPHA)
        for x in range(200):
            a = int(60 * math.sin(x / 200 * math.pi))
            pygame.draw.line(div, (0, 180, 180, a), (x, 0), (x, 0))
        screen.blit(div, (WIDTH // 2 - 100, stat_y))

        hs = font_small.render(f"★ 最高分: {self.highscore}", True, YELLOW)
        screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, stat_y + 14))

        total_m = int(self.total_time // 60)
        total_s = int(self.total_time % 60)
        tt = font_small.render(f"总游戏时间: {total_m}:{total_s:02d}", True, (140, 150, 170))
        screen.blit(tt, (WIDTH // 2 - tt.get_width() // 2, stat_y + 36))

        # Version / hint at very bottom
        hint = font_small.render("WASD / 方向键 控制 空格确认", True, (120, 140, 170))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 30))

        # ---- CONFIRMATION DIALOG ----
        if self.confirm_reset:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            dw, dh = 340, 180
            dx, dy = WIDTH // 2 - dw // 2, HEIGHT // 2 - dh // 2

            # Dialog background
            dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
            pygame.draw.rect(dlg, (15, 15, 35, 245), (0, 0, dw, dh), border_radius=10)
            pygame.draw.rect(dlg, (220, 40, 60, 180), (0, 0, dw, dh), 2, border_radius=10)
            screen.blit(dlg, (dx, dy))

            msg = font.render("重置所有数据？", True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 50))

            sub = font_small.render("最高分和游戏时间将被清空", True, GRAY)
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 10))

            choices = ["确 定", "取 消"]
            cbw, cbh = 110, 38
            for i, ch in enumerate(choices):
                cbx = WIDTH // 2 - 140 + i * 170
                cby = HEIGHT // 2 + 20
                if i == self.reset_sel:
                    cbtn = pygame.Surface((cbw, cbh), pygame.SRCALPHA)
                    cc = (220, 40, 60) if i == 0 else (80, 160, 80)
                    pygame.draw.rect(cbtn, (*cc, 100), (0, 0, cbw, cbh), border_radius=6)
                    pygame.draw.rect(cbtn, (*cc, 220), (0, 0, cbw, cbh), 2, border_radius=6)
                    screen.blit(cbtn, (cbx, cby))
                ct = font.render(ch, True, WHITE if i == self.reset_sel else GRAY)
                screen.blit(ct, (cbx + cbw // 2 - ct.get_width() // 2, cby + cbh // 2 - ct.get_height() // 2))

        # ---- MOUSE CONTROL DIALOG ----
        if self.ask_mouse:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            dw, dh = 360, 180
            dx, dy = WIDTH // 2 - dw // 2, HEIGHT // 2 - dh // 2

            dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
            pygame.draw.rect(dlg, (15, 15, 35, 245), (0, 0, dw, dh), border_radius=10)
            pygame.draw.rect(dlg, (0, 180, 220, 180), (0, 0, dw, dh), 2, border_radius=10)
            screen.blit(dlg, (dx, dy))

            msg = font.render("启用鼠标控制飞机？", True, WHITE)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 60))

            sub = font_small.render("鼠标模式: 左键射击  键盘模式: 空格射击", True, GRAY)
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 20))

            choices = ["是", "否"]
            cbw, cbh = 110, 38
            for i, ch in enumerate(choices):
                cbx = WIDTH // 2 - 140 + i * 170
                cby = HEIGHT // 2 + 10
                if i == self.ask_mouse_sel:
                    cbtn = pygame.Surface((cbw, cbh), pygame.SRCALPHA)
                    cc = (0, 180, 220) if i == 0 else (220, 40, 60)
                    pygame.draw.rect(cbtn, (*cc, 100), (0, 0, cbw, cbh), border_radius=6)
                    pygame.draw.rect(cbtn, (*cc, 220), (0, 0, cbw, cbh), 2, border_radius=6)
                    screen.blit(cbtn, (cbx, cby))
                ct = font.render(ch, True, WHITE if i == self.ask_mouse_sel else GRAY)
                screen.blit(ct, (cbx + cbw // 2 - ct.get_width() // 2, cby + cbh // 2 - ct.get_height() // 2))

        # ---- SETTINGS DIALOG ----
        if self.show_settings:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            dw, dh = 320, 180
            dx, dy = WIDTH // 2 - dw // 2, HEIGHT // 2 - dh // 2
            dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
            pygame.draw.rect(dlg, (15, 15, 35, 245), (0, 0, dw, dh), border_radius=10)
            pygame.draw.rect(dlg, (0, 180, 220, 180), (0, 0, dw, dh), 2, border_radius=10)
            screen.blit(dlg, (dx, dy))

            ttl = font.render("设 置", True, WHITE)
            screen.blit(ttl, (WIDTH // 2 - ttl.get_width() // 2, HEIGHT // 2 - 70))

            vol = font.render(f"音量: {self._volume}", True, CYAN)
            screen.blit(vol, (WIDTH // 2 - vol.get_width() // 2, HEIGHT // 2 - 20))

            bar_w, bar_h = 200, 12
            bar_x = WIDTH // 2 - bar_w // 2
            bar_y = HEIGHT // 2 + 10
            pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            fill = int(bar_w * self._volume / 10)
            if fill > 0:
                c = (0, 255, 100) if self._volume > 5 else (255, 200, 60)
                pygame.draw.rect(screen, c, (bar_x, bar_y, fill, bar_h), border_radius=6)
            pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

            hint = font_small.render("← → 调整  空格/ESC 返回", True, GRAY)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 40))

    def draw_game(self, ox, oy):
        game_srf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        game_srf.fill((0, 0, 0, 0))

        # Powerups
        for p in self.powerups:
            p.draw(game_srf)

        # Enemies
        for e in self.enemies:
            e.draw(game_srf)

        # Enemy bullets
        for b in self.enemy_bullets:
            b.draw(game_srf)

        # Player
        self.player.draw(game_srf)

        # Player bullets
        for b in self.player.bullets:
            b.draw(game_srf)

        # Particles
        for p in self.particles:
            p.draw(game_srf)

        # Floating texts
        for f in self.floats:
            f.draw(game_srf)

        # HUD - draw on screen directly (no offset)
        screen.blit(game_srf, (ox, oy))
        self.draw_hud()

        # Crosshair (mouse control mode only)
        if self.mouse_control:
            mx, my = pygame.mouse.get_pos()
            pygame.draw.line(screen, RED, (mx - 8, my), (mx - 3, my), 2)
            pygame.draw.line(screen, RED, (mx + 3, my), (mx + 8, my), 2)
            pygame.draw.line(screen, RED, (mx, my - 8), (mx, my - 3), 2)
            pygame.draw.line(screen, RED, (mx, my + 3), (mx, my + 8), 2)
            pygame.draw.circle(screen, WHITE, (mx, my), 2, 1)

    def draw_hud(self):
        # Score
        score_surf = font.render(f"{self.score}", True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - score_surf.get_width() // 2, 12))

        score_label = font_small.render("分数", True, GRAY)
        screen.blit(score_label, (WIDTH // 2 - score_label.get_width() // 2, 40))

        # Time
        mins = int(self.play_time // 60)
        secs = int(self.play_time % 60)
        time_str = f"{mins}:{secs:02d}"
        time_surf = font_small.render(time_str, True, GRAY)
        screen.blit(time_surf, (WIDTH - time_surf.get_width() - 10, 10))

        # High score
        hs = font_small.render(f"最高 {self.highscore}", True, GRAY)
        screen.blit(hs, (WIDTH - hs.get_width() - 10, 28))

        # Lives
        for i in range(self.player.lives):
            screen.blit(SPRITES["life"], (15 + i * 22, 8))

        # Combo
        if self.combo > 0:
            combo_surf = font_small.render(f"连击 x{self.combo}", True, YELLOW)
            screen.blit(combo_surf, (WIDTH // 2 - combo_surf.get_width() // 2, 60))
            bar_w = 120
            bar_h = 6
            bar_x = WIDTH // 2 - bar_w // 2
            bar_y = 82
            ratio = self.combo_timer / 120.0
            pygame.draw.rect(screen, GRAY, (bar_x, bar_y, bar_w, bar_h))
            if ratio > 0:
                color = YELLOW if ratio > 0.3 else RED
                pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * ratio), bar_h))
            pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

        # Power-up timers (right side)
        pwr_y = 50
        if self.player.power > 0:
            t = self.player.stack_time("spread")
            txt = font_small.render(f"散射 Lv{self.player.power} {t}s", True, ORANGE)
            screen.blit(txt, (WIDTH - txt.get_width() - 10, pwr_y))
            pwr_y += 18
        if self.player.shoot_delay < 10:
            t = self.player.stack_time("rapid")
            txt = font_small.render(f"速射 {t}s", True, CYAN)
            screen.blit(txt, (WIDTH - txt.get_width() - 10, pwr_y))
            pwr_y += 18
        if self.player.shield > 0:
            t = self.player.stack_time("shield")
            txt = font_small.render(f"护盾 x{self.player.shield} {t}s", True, BLUE)
            screen.blit(txt, (WIDTH - txt.get_width() - 10, pwr_y))
            pwr_y += 18

        # Boss HP bar (top center)
        if self.boss_active:
            for e in self.enemies:
                if isinstance(e, Boss):
                    bw, bh = 300, 12
                    bx = WIDTH // 2 - bw // 2
                    by = 105
                    pygame.draw.rect(screen, (40, 0, 0), (bx, by, bw, bh), border_radius=6)
                    fill = int(bw * e.hp / e.max_hp)
                    if fill > 0:
                        color = (255, 60, 60) if e.hp < e.max_hp * 0.3 else (255, 200, 60)
                        pygame.draw.rect(screen, color, (bx, by, fill, bh), border_radius=6)
                    pygame.draw.rect(screen, WHITE, (bx, by, bw, bh), 1, border_radius=6)
                    name_t = font_small.render(f"BOSS ({e.hp}/{e.max_hp})", True, WHITE)
                    screen.blit(name_t, (bx + bw // 2 - name_t.get_width() // 2, by - 16))
                    break

    def draw_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        over = font_big.render("游 戏 结 束", True, RED)
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 90))

        score_text = font.render(f"最终得分: {self.score}", True, WHITE)
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 - 10))

        mins = int(self.play_time // 60)
        secs = int(self.play_time % 60)
        time_text = font.render(f"存活时间: {mins}:{secs:02d}", True, WHITE)
        screen.blit(time_text, (WIDTH // 2 - time_text.get_width() // 2, HEIGHT // 2 + 30))

        if self.score >= self.highscore:
            new_record = font.render("★ 新纪录！", True, YELLOW)
            screen.blit(new_record, (WIDTH // 2 - new_record.get_width() // 2, HEIGHT // 2 + 70))

        seconds = max(1, (self.gameover_timer // 60) + 1)
        hint = font.render(f"返回菜单 ({seconds}s) 空格跳过", True, WHITE)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 100))

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        if self.input_mode:
            mode = "导出" if self.input_mode == "export" else "导入"
            title = font_big.render(f"{mode}存档", True, WHITE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))

            hint = font_small.render("输入文件名 (不含扩展名)", True, GRAY)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 260))

            iw, ih = 300, 40
            ix, iy = WIDTH // 2 - iw // 2, 290
            pygame.draw.rect(screen, GRAY, (ix, iy, iw, ih), 2)
            txt = font.render(self.input_text + ("_" if pygame.time.get_ticks() % 800 < 400 else " "), True, WHITE)
            screen.blit(txt, (ix + 8, iy + ih // 2 - txt.get_height() // 2))

            hint2 = font_small.render("回车确认  ESC取消", True, GRAY)
            screen.blit(hint2, (WIDTH // 2 - hint2.get_width() // 2, 350))
        else:
            title = font_big.render("暂停", True, WHITE)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))

            options = ["继续游戏", "重新开始本局", "退出到菜单", "导出存档", "导入存档"]
            start_y = 290
            for i, opt in enumerate(options):
                by = start_y + i * 48
                if i == self.pause_sel:
                    pulse = int(3 + 2 * math.sin(pygame.time.get_ticks() * 0.006))
                    bg = pygame.Surface((260, 40), pygame.SRCALPHA)
                    pygame.draw.rect(bg, (0, 180, 220, 60), (0, 0, 260, 40), border_radius=6)
                    screen.blit(bg, (WIDTH // 2 - 130 - pulse, by - pulse))
                    border = pygame.Surface((260 + pulse * 2, 40 + pulse * 2), pygame.SRCALPHA)
                    pygame.draw.rect(border, (0, 200, 240, 200), (0, 0, 260 + pulse * 2, 40 + pulse * 2), 2, border_radius=8)
                    screen.blit(border, (WIDTH // 2 - 130 - pulse, by - pulse))
                t = font.render(opt, True, WHITE if i == self.pause_sel else GRAY)
                screen.blit(t, (WIDTH // 2 - t.get_width() // 2, by))

            hint = font_small.render("ESC 返回  ↑↓ 选择  空格 确认", True, GRAY)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 40))

    def _input_confirm(self):
        path = os.path.join(os.path.dirname(__file__), self.input_text + ".json")
        mode = self.input_mode
        if self.input_mode == "export":
            r = export_save(self.total_time, path)
            if r:
                self.toast_msg = f"导出成功: {self.input_text}.json"
            else:
                self.toast_msg = "导出失败"
        elif self.input_mode == "import":
            ok = import_save(path)
            if ok:
                self.highscore = load_highscore()
                self.total_time = _total_time_import
                self.toast_msg = f"导入成功: {self.input_text}.json"
            else:
                self.toast_msg = "导入失败: 文件不存在"
        self.input_mode = None
        self.input_text = ""
        self.toast_timer = 120

    def _game_update(self, keys):
        self.play_time += 1 / 60
        self.total_time += 1 / 60
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        self.player.update(keys, self.mouse_x, self.mouse_y, self.mouse_control)
        dt = 1 / 60

        # Combo timer
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        # Difficulty
        self.difficulty = 1 + self.score // 200

        # Spawn enemies
        spawn_rate = max(15, 60 - self.difficulty * 3 - self.score // 100)
        self.spawn_timer += 1
        if self.spawn_timer >= spawn_rate:
            self.spawn_enemy()
            self.spawn_timer = 0

        # Boss check + warning
        if self.score > 0 and self.score % 500 < 10 and not self.boss_spawned and not self.boss_active:
            self.spawn_boss()
            self.boss_spawned = True
        if self.score % 500 >= 10:
            self.boss_spawned = False
        if self.score > 0 and 500 - (self.score % 500) <= 80 and 500 - (self.score % 500) > 0 and not self.boss_spawned and not self.boss_active:
            if self.boss_warning == 0:
                self.boss_warning = 79

        # Update enemies
        for e in self.enemies[:]:
            e.update()
            if e.offscreen():
                self.enemies.remove(e)
                if isinstance(e, Boss):
                    self.boss_active = False
                continue

            # Enemy shoots
            if isinstance(e, (Fighter, Bomber, Boss)) and e.shoot_timer <= 0 and e.y > 0:
                self.enemy_bullets.append(EnemyBullet(
                    e.x + e.w // 2, e.y + e.h,
                    self.player.x + self.player.w // 2,
                    self.player.y + self.player.h // 2
                ))
                e.shoot_timer = random.randint(60, 180) - self.difficulty * 5

            if isinstance(e, Boss) and e.phase == 2:
                for i in range(-1, 2):
                    self.enemy_bullets.append(EnemyBullet(
                        e.x + e.w // 2 + i * 15, e.y + e.h,
                        self.player.x + self.player.w // 2 + i * 30,
                        self.player.y + self.player.h // 2
                    ))
                e.phase_timer = -30

            # Bullet-enemy collision
            for b in self.player.bullets[:]:
                if collide(b, e):
                    if e.hit():
                        self.add_explosion(e.x + e.w // 2, e.y + e.h // 2, ORANGE)
                        play_sound(snd_hit)
                        pts = e.score_val * (1 + self.combo // 5)
                        self.score += pts
                        self.combo += 1
                        self.combo_timer = 120
                        self.screen_shake = 8
                        self.floats.append(FloatingText(e.x + e.w // 2, e.y, f"+{pts}"))

                        # Combo milestone flash
                        if self.combo in (5, 10, 20, 30, 50):
                            self.flashes.append(ScreenFlash(YELLOW, 20))
                            self.floats.append(FloatingText(WIDTH // 2, HEIGHT // 2, f"连击 x{self.combo}!", ORANGE))

                        # Drop powerup
                        if random.random() < e.drop_rate:
                            self.powerups.append(PowerUp(e.x, e.y))
                        elif random.random() < 0.04:
                            self.powerups.append(PowerUp(e.x, e.y))

                        self.enemies.remove(e)
                        if isinstance(e, Boss):
                            self.boss_active = False
                    self.player.bullets.remove(b)
                    break

            # Enemy-player collision
            if e in self.enemies and collide(self.player.rect(), e):
                self.add_explosion(e.x + e.w // 2, e.y + e.h // 2, RED, 20)
                self.hit_flash = 12
                if self.player.hit():
                    self.hit_flash = 0
                    self.flashes.clear()
                    self.state = "gameover"
                    self.gameover_timer = 180
                    self.add_explosion(self.player.x + self.player.w // 2, self.player.y + self.player.h // 2, GREEN, 25)
                self.enemies.remove(e)
                if isinstance(e, Boss):
                    self.boss_active = False

            # Boss shoot more
            if isinstance(e, Boss) and e.phase == 1 and e.shoot_timer % 30 == 0 and e.y > 0:
                self.enemy_bullets.append(EnemyBullet(
                    e.x + e.w // 2, e.y + e.h,
                    self.player.x + self.player.w // 2,
                    self.player.y + self.player.h // 2
                ))

        # Update enemy bullets
        for b in self.enemy_bullets[:]:
            b.update()
            if b.offscreen():
                self.enemy_bullets.remove(b)
                continue
            if collide(b, self.player.rect()):
                self.enemy_bullets.remove(b)
                self.add_explosion(b.x, b.y, RED, 6)
                self.hit_flash = 12
                if self.player.hit():
                    self.hit_flash = 0
                    self.flashes.clear()
                    self.state = "gameover"
                    self.gameover_timer = 180
                    self.add_explosion(self.player.x + self.player.w // 2, self.player.y + self.player.h // 2, GREEN, 25)

        # Update powerups
        for p in self.powerups[:]:
            p.update()
            if p.y > HEIGHT:
                self.powerups.remove(p)
                continue
            if collide(p, self.player.rect()):
                play_sound(snd_powerup)
                self.player.add_stack(p.type)
                self.powerups.remove(p)

        # Particles
        for p in self.particles[:]:
            p.update(dt)
            if p.done():
                self.particles.remove(p)

        # Screen shake
        if self.screen_shake > 0:
            self.screen_shake -= 1

        # Floating texts
        for f in self.floats[:]:
            f.update()
            if f.done():
                self.floats.remove(f)

        # Screen flashes (combo)
        for f in self.flashes[:]:
            f.update()
            if not f.alive():
                self.flashes.remove(f)

        # Hit flash
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Boss warning countdown
        if self.boss_warning > 0:
            self.boss_warning -= 1

    def run(self):
        pygame.mouse.set_visible(True)
        running = True
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            self.update(events)
            self.draw()
            _log_flush()
            clock.tick(60)

        _log_flush()
        pygame.mouse.set_visible(True)
        pygame.quit()

if __name__ == "__main__":
    import traceback
    try:
        game = Game()
        game.run()
    except Exception:
        with open(os.path.join(os.path.dirname(__file__), "crash.log"), "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        input("发生错误！请截图此窗口并按回车退出...")
