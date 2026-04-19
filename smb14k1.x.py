import pygame
import sys
import random

# ==========================================
# Constants & Configuration (Python 3.14+)
# ==========================================
FPS = 60
BLOCK_SIZE = 32
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 14 * BLOCK_SIZE  # 14 blocks high (448 pixels)

# Base Colors (ground / UI; tiles use NES_* below)
GROUND_BROWN = (248, 216, 120)
BRICK_BROWN = (200, 76, 12)
QUESTION_GOLD = (248, 216, 32)
PIPE_GREEN = (0, 200, 0)
FLAG_WHITE = (248, 248, 248)
# SMB1 NES PPU–style hues (procedural sprites; no image files)
SMB1_BLACK = (0, 0, 0)
SMB1_RED = (216, 40, 0)
SMB1_RED_D = (152, 32, 0)
SMB1_SKIN = (252, 188, 120)
SMB1_BLUE = (0, 88, 248)
SMB1_BLUE_D = (0, 56, 152)
SMB1_POLE = (48, 168, 56)
SMB1_POLE_D = (32, 112, 40)
SMB1_FLAG_ORANGE = (248, 152, 32)
SMB1_FLAG_WHITE = (248, 248, 248)
# NES overworld–style tile palette (procedural, no image files)
NES_GRASS_L = (136, 224, 56)
NES_GRASS_D = (72, 152, 0)
NES_GRASS_M = (104, 184, 32)
NES_GROUND_T = (200, 120, 72)
NES_GROUND_D = (152, 72, 24)
NES_GROUND_DD = (120, 48, 8)
NES_BRICK = (200, 76, 12)
NES_BRICK_H = (248, 140, 80)
NES_MORTAR = (60, 28, 8)
NES_Q_YELLOW = (248, 184, 0)
NES_Q_YELLOW_D = (216, 136, 0)
NES_Q_RIVET = (152, 72, 24)
NES_PIPE_L = (0, 184, 0)
NES_PIPE_D = (0, 120, 0)
NES_PIPE_H = (144, 248, 144)
NES_STONE = (168, 168, 176)
NES_STONE_D = (120, 120, 128)
NES_GOOMBA = (196, 96, 32)
NES_GOOMBA_D = (136, 56, 0)
NES_GOOMBA_MOUTH = (252, 188, 120)
NES_GOOMBA_EYE = (252, 252, 252)
NES_GOOMBA_FANG = (252, 252, 200)

# Physics
GRAVITY = 0.5
MAX_FALL_SPEED = 12
PLAYER_SPEED = 5
JUMP_FORCE = -10.5

# ==========================================
# Procedural Level Generation (1-1 to 8-4)
# ==========================================
def generate_level_data(world: int, level: int):
    """Procedurally generates a level array and enemy spawns based on world/level."""
    # Consistent seed so the "same" level is generated each time you play it
    random.seed(world * 100 + level)
    
    width = 100 + (world * 20) + (level * 10)
    level_map = [[" " for _ in range(width)] for _ in range(14)]
    enemies_pos = []

    def put(char: str, x: int, y: int, w: int = 1, h: int = 1):
        for i in range(w):
            for j in range(h):
                if 0 <= y + j < 14 and 0 <= x + i < width:
                    level_map[y + j][x + i] = char

    # Generate Ground with Pits
    x = 0
    while x < width:
        # Pits spawn between x=10 and the end zone. Pit probability scales with the world.
        if 10 < x < width - 20 and random.random() < (0.04 + world * 0.01):
            gap_size = random.randint(1, 2) # 1 to 2 block wide gaps
            x += gap_size
        else:
            put("G", x, 12, 1, 2)
            x += 1

    # Generate Obstacles, Enemies, and Mario-Height Pipes
    for x in range(15, width - 20, 7):
        if level_map[12][x] == "G" and level_map[12][x+1] == "G":
            choice = random.random()
            if choice < 0.15:
                # All pipes are exactly Mario's height (1 block tall)
                put("P", x, 11, 2, 1) 
                enemies_pos.append((x + 3, 11))
            elif choice < 0.35:
                put("B", x, 8, 3, 1)
                if random.random() < 0.5:
                    put("Q", x+1, 8)
            elif choice < 0.5:
                put("S", x, 11); put("S", x+1, 10, 1, 2); put("S", x+2, 9, 1, 3)
                if random.random() < 0.5:
                    enemies_pos.append((x + 4, 11))
            elif choice < 0.7:
                enemies_pos.append((x, 11))

    # Generate Flagpole Area at the end
    flag_x = width - 8
    
    # Pre-flag stairs
    for i in range(5):
        put("S", flag_x - 7 + i, 11 - i, 1, i + 1)
    # Flag top (touch completes level) + pole segments (SMB1-style end)
    put("F", flag_x, 2)
    for fy in range(3, 12):
        put("|", flag_x, fy)

    # Ensure solid ground under the stairs and flagpole
    for gx in range(flag_x - 8, width):
        put("G", gx, 12, 1, 2)

    return level_map, enemies_pos

# ==========================================
# Game Objects
# ==========================================
def _draw_smb1_small_mario(surface: pygame.Surface, dest: pygame.Rect, facing_right: bool):
    """SMB1 small Mario (10x16 NES silhouette); square pixels; eyes embedded so flipping works."""
    pattern = [
        "...RRRR...",
        "..RRRRRR..",
        ".HHHssss..",
        ".HHssssss.",
        ".HHssesse.",
        "..sssssss.",
        "..sssssss.",
        "..sssss...",
        "...RRRR...",
        "..RRBRRR..",
        ".RRRBBRRR.",
        "bbRBBBBRbb",
        "bbBBBBBBbb",
        "..BB..BB..",
        ".bb....bb.",
        "bbb....bbb",
    ]
    ch_map = {
        "R": SMB1_RED,
        "r": SMB1_RED_D,
        "H": SMB1_BLACK,
        "s": SMB1_SKIN,
        "e": SMB1_BLACK,
        "B": SMB1_BLUE,
        "b": SMB1_BLUE_D,
        ".": None,
    }
    _blit_pattern(surface, dest, pattern, ch_map, flip_x=not facing_right)


def _draw_flagpole_tile(surface: pygame.Surface, rect: pygame.Rect, is_top: bool):
    """SMB1 flag-top (ball + orange/white striped flag) and pole segments using square pixels."""
    if is_top:
        pat = [
            "....pPp.....",
            "...pPPPp....",
            "...pPPPp....",
            "....pPp.....",
            ".....P......",
            ".....PFFFFF.",
            ".....PFFFFW.",
            ".....PFWWWW.",
            ".....PFFFFW.",
            ".....PFFFFF.",
            ".....P......",
            ".....P......",
        ]
        cmap = {
            ".": None,
            "p": SMB1_POLE_D,
            "P": SMB1_POLE,
            "F": SMB1_FLAG_ORANGE,
            "W": SMB1_FLAG_WHITE,
        }
        _blit_pattern(surface, rect, pat, cmap)
    else:
        pat = [
            ".....P......",
            ".....P......",
            ".....P......",
            ".....P......",
            ".....P......",
            ".....P......",
            ".....P......",
            ".....P......",
        ]
        cmap = {".": None, "P": SMB1_POLE}
        _blit_pattern(surface, rect, pat, cmap)


def _blit_pattern(
    surface: pygame.Surface,
    dest: pygame.Rect,
    rows: list[str],
    ch_map: dict,
    flip_x: bool = False,
) -> None:
    """Scale string rows into dest. Square pixels (NES-like): same scale on X and Y."""
    if not rows:
        return
    h = len(rows)
    w = len(rows[0])
    s = max(1, min(dest.width // w, dest.height // h))
    sx = sy = s
    ox = dest.x + (dest.width - w * sx) // 2
    oy = dest.y + (dest.height - h * sy) // 2
    for ry, row in enumerate(rows):
        cols = list(row)
        if flip_x:
            cols = cols[::-1]
        for cx, ch in enumerate(cols):
            col = ch_map.get(ch)
            if col is not None:
                pygame.draw.rect(surface, col, (ox + cx * sx, oy + ry * sy, sx, sy))


def _draw_tile_smb1(surface: pygame.Surface, rect: pygame.Rect, ttype: str, gx: int, gy: int) -> None:
    """Procedural SMB1 overworld–style tiles (no external assets)."""
    blk = SMB1_BLACK

    if ttype == "G":
        pat = [
            "LLLLLLLL",
            "LlLlLlLl",
            "mmmmmmmm",
            "TTTTTTTT",
            "DDDDDDDD",
            "DdDdDdDd",
            "DDDDDDDD",
            "DDDDDDDD",
        ]
        cmap = {
            "L": NES_GRASS_L, "l": NES_GRASS_D, "m": NES_GRASS_M,
            "T": NES_GROUND_T, "D": NES_GROUND_D, "d": NES_GROUND_DD,
        }
        _blit_pattern(surface, rect, pat, cmap)
        pygame.draw.rect(surface, blk, rect, 1)
        return

    if ttype == "B":
        pat = [
            "########",
            "#BBBBhB#",
            "#BBBBhB#",
            "mmmmmmmm",
            "#hBBBBB#",
            "#hBBBBB#",
            "mmmmmmmm",
            "########",
        ]
        cmap = {"#": blk, "B": NES_BRICK, "h": NES_BRICK_H, "m": NES_MORTAR}
        _blit_pattern(surface, rect, pat, cmap)
        return

    if ttype == "Q":
        pat = [
            "########",
            "#rYYYYr#",
            "#YbbbbY#",
            "#YYYbYY#",
            "#YYbYYY#",
            "#YYYYYY#",
            "#YYbYYY#",
            "#rYYYYr#",
        ]
        cmap = {
            "#": blk,
            "Y": NES_Q_YELLOW,
            "y": NES_Q_YELLOW_D,
            "r": NES_Q_RIVET,
            "b": blk,
        }
        _blit_pattern(surface, rect, pat, cmap)
        return

    if ttype == "P":
        pat = [
            "##pppp##",
            "#pLLLLp#",
            "#pLHHLp#",
            "#pLLLLp#",
            "#pLLLLp#",
            "#pLLLLp#",
            "#pLLLLp#",
            "##pppp##",
        ]
        cmap = {"#": blk, "p": NES_PIPE_D, "L": NES_PIPE_L, "H": NES_PIPE_H}
        _blit_pattern(surface, rect, pat, cmap, flip_x=(gx % 2 == 1))
        return

    if ttype == "S":
        pat = [
            "########",
            "#SsSsSs#",
            "#sSsSsS#",
            "#SsSsSs#",
            "#sSsSsS#",
            "#SsSsSs#",
            "#sSsSsS#",
            "########",
        ]
        cmap = {"#": blk, "S": NES_STONE, "s": NES_STONE_D}
        _blit_pattern(surface, rect, pat, cmap)
        return


def _draw_goomba_smb1(surface: pygame.Surface, dest: pygame.Rect, frame: int, facing_right: bool) -> None:
    """SMB1 Goomba (12x8 NES proportions); eyes/brows/fangs embedded; two walk frames; flip on direction."""
    blk = SMB1_BLACK
    f0 = [
        "....GGGG....",
        "...GGGGGG...",
        "..GGGGGGGG..",
        ".GbWWbbWWbG.",
        ".GWBWGGWBWG.",
        ".GGfGGGGfGG.",
        "..GGG..GGG..",
        "..GG....GG..",
    ]
    f1 = [
        "....GGGG....",
        "...GGGGGG...",
        "..GGGGGGGG..",
        ".GbWWbbWWbG.",
        ".GWBWGGWBWG.",
        ".GGfGGGGfGG.",
        "..GGG..GGG..",
        "GGG......GGG",
    ]
    pat = f0 if frame == 0 else f1
    cmap = {
        "G": NES_GOOMBA,
        "g": NES_GOOMBA_D,
        "b": blk,
        "B": blk,
        "W": NES_GOOMBA_EYE,
        "f": NES_GOOMBA_FANG,
        "o": NES_GOOMBA_MOUTH,
        ".": None,
    }
    _blit_pattern(surface, dest, pat, cmap, flip_x=facing_right)


class Player:
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, BLOCK_SIZE * 0.8, BLOCK_SIZE * 0.9)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.is_jumping = False
        self.is_dead = False
        self.facing_right = True

    def update(self, tiles: list[pygame.Rect]):
        if self.is_dead:
            self.vel_y += GRAVITY
            self.rect.y += int(self.vel_y)
            return

        # X Movement
        if self.vel_x > 0.5:
            self.facing_right = True
        elif self.vel_x < -0.5:
            self.facing_right = False
        self.rect.x += int(self.vel_x)
        self._check_collisions(tiles, dx=True)

        # Y Movement (Gravity)
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED
            
        self.rect.y += int(self.vel_y)
        self._check_collisions(tiles, dy=True)

        # Bottom pit death
        if self.rect.top > SCREEN_HEIGHT:
            self.is_dead = True

    def _check_collisions(self, tiles: list[pygame.Rect], dx: bool = False, dy: bool = False):
        for tile in tiles:
            if self.rect.colliderect(tile):
                if dx:
                    if self.vel_x > 0:  self.rect.right = tile.left
                    elif self.vel_x < 0: self.rect.left = tile.right
                if dy:
                    if self.vel_y > 0:
                        self.rect.bottom = tile.top
                        self.vel_y = 0
                        self.is_jumping = False
                    elif self.vel_y < 0:
                        self.rect.top = tile.bottom
                        self.vel_y = 0

    def jump(self):
        if self.is_dead:
            return
        if not self.is_jumping:
            self.vel_y = JUMP_FORCE
            self.is_jumping = True

    def draw(self, surface: pygame.Surface, camera_x: int):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        _draw_smb1_small_mario(surface, draw_rect, self.facing_right)

class Enemy:
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, BLOCK_SIZE * 0.8, BLOCK_SIZE * 0.8)
        self.vel_x = -1.5
        self.vel_y = 0.0
        self.is_active = True

    def update(self, tiles: list[pygame.Rect]):
        if not self.is_active: return
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)
        self._check_collisions(tiles, dy=True)
        self.rect.x += int(self.vel_x)
        self._check_collisions(tiles, dx=True)
        if self.rect.top > SCREEN_HEIGHT:
            self.is_active = False

    def _check_collisions(self, tiles: list[pygame.Rect], dx: bool = False, dy: bool = False):
        for tile in tiles:
            if self.rect.colliderect(tile):
                if dx:
                    self.vel_x *= -1 
                    if self.vel_x > 0: self.rect.left = tile.right
                    else: self.rect.right = tile.left
                if dy:
                    if self.vel_y > 0:
                        self.rect.bottom = tile.top
                        self.vel_y = 0

    def draw(self, surface: pygame.Surface, camera_x: int):
        if self.is_active:
            draw_rect = self.rect.copy()
            draw_rect.x -= camera_x
            frame = (pygame.time.get_ticks() // 200) % 2
            facing_right = self.vel_x > 0
            _draw_goomba_smb1(surface, draw_rect, frame, facing_right)

# ==========================================
# Title screen (SMB1-style flow; no external assets)
# ==========================================
def draw_title_screen(surface: pygame.Surface, world: int, level: int) -> None:
    """Overworld-style title: clouds, ground band, NES-like copy, blink START, deco Mario/Goomba."""
    sky = (92, 148, 252)
    surface.fill(sky)
    for cx, cy, ew, eh in ((60, 50, 130, 48), (320, 36, 110, 42), (560, 70, 100, 44)):
        ell = pygame.Rect(cx, cy, ew, eh)
        pygame.draw.ellipse(surface, (252, 252, 255), ell)
        pygame.draw.ellipse(surface, (228, 236, 248), ell.inflate(-10, -8))
    ground_y = SCREEN_HEIGHT - 2 * BLOCK_SIZE
    for gx in range(0, SCREEN_WIDTH, BLOCK_SIZE):
        col = gx // BLOCK_SIZE
        r0 = pygame.Rect(gx, ground_y, BLOCK_SIZE, BLOCK_SIZE)
        _draw_tile_smb1(surface, r0, "G", col, 12)
        r1 = pygame.Rect(gx, ground_y + BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        _draw_tile_smb1(surface, r1, "G", col, 13)
    for bx in range(3 * BLOCK_SIZE, SCREEN_WIDTH - 3 * BLOCK_SIZE, BLOCK_SIZE * 2):
        br = pygame.Rect(bx, ground_y - BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
        _draw_tile_smb1(surface, br, "B", bx // BLOCK_SIZE, 10)

    try:
        title_font = pygame.font.SysFont("arial", 34, bold=True)
        sub_font = pygame.font.SysFont("arial", 22, bold=True)
        hint_font = pygame.font.SysFont("arial", 16)
    except Exception:
        title_font = pygame.font.Font(None, 34)
        sub_font = pygame.font.Font(None, 22)
        hint_font = pygame.font.Font(None, 16)

    white = FLAG_WHITE
    title_s = title_font.render("SUPER MARIO BROS.", True, white)
    sub_s = sub_font.render("AC'S SMB1 PY PORT 0.1", True, QUESTION_GOLD)
    world_s = sub_font.render(f"WORLD  {world}-{level}", True, white)
    blink_on = (pygame.time.get_ticks() // 400) % 2 == 0
    start_s = sub_font.render("PRESS START", True, (252, 252, 120)) if blink_on else None
    help_s = hint_font.render("SPACE or ENTER —  LEFT / RIGHT: world   UP / DOWN: level", True, (60, 72, 120))

    surface.blit(title_s, title_s.get_rect(center=(SCREEN_WIDTH // 2, 100)))
    surface.blit(sub_s, sub_s.get_rect(center=(SCREEN_WIDTH // 2, 145)))
    surface.blit(world_s, world_s.get_rect(center=(SCREEN_WIDTH // 2, 200)))
    if start_s:
        surface.blit(start_s, start_s.get_rect(center=(SCREEN_WIDTH // 2, 255)))
    surface.blit(help_s, help_s.get_rect(center=(SCREEN_WIDTH // 2, 300)))

    mario_r = pygame.Rect(72, ground_y - 110, int(BLOCK_SIZE * 0.85), int(BLOCK_SIZE * 0.95))
    _draw_smb1_small_mario(surface, mario_r, True)
    goom_r = pygame.Rect(SCREEN_WIDTH - 140, ground_y - 100, int(BLOCK_SIZE * 0.85), int(BLOCK_SIZE * 0.85))
    _draw_goomba_smb1(surface, goom_r, 0, False)


# ==========================================
# Main Engine
# ==========================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Game State Variables
    game_state = "title"  # "title" | "playing"
    world = 1
    level = 1
    camera_x = 0
    level_width_pixels = 0
    level_clearing = False
    clear_timer = 0
    
    tiles = []
    enemies = []
    player = Player(100, 100)
    current_sky_color = (92, 148, 252)

    tile_colors = {
        "G": GROUND_BROWN, "B": BRICK_BROWN, "Q": QUESTION_GOLD,
        "P": PIPE_GREEN, "S": BRICK_BROWN, "F": FLAG_WHITE, "|": (160, 160, 168),
    }

    def init_level():
        nonlocal tiles, enemies, player, camera_x, level_width_pixels, current_sky_color, level_clearing, clear_timer
        level_clearing = False
        clear_timer = 0
        
        # Determine Sky Color based on World
        if world in (2, 6): current_sky_color = (0, 0, 40)       # Night
        elif world in (3, 7): current_sky_color = (150, 200, 255) # Snow
        elif world == 4: current_sky_color = (255, 140, 0)        # Sunset
        elif world == 8: current_sky_color = (0, 0, 0)            # Castle
        else: current_sky_color = (92, 148, 252)                  # Day

        pygame.display.set_caption("AC'S SMB1 PY PORT 0.1")
        
        level_map, enemies_pos = generate_level_data(world, level)
        level_width_pixels = len(level_map[0]) * BLOCK_SIZE

        tiles.clear()
        for y, row in enumerate(level_map):
            for x, char in enumerate(row):
                if char != " ":
                    tiles.append({
                        "rect": pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                        "type": char,
                        "gx": x,
                        "gy": y,
                    })

        player = Player(100, 100)
        enemies.clear()
        for ex, ey in enemies_pos:
            enemies.append(Enemy(ex * BLOCK_SIZE, ey * BLOCK_SIZE))
        
        camera_x = 0

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game_state == "title":
                    # Left/Right = world 1–8 (wrap); Up/Down = level 1–4 (wrap). Space/Enter starts.
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        world = 8 if world <= 1 else world - 1
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        world = 1 if world >= 8 else world + 1
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        level = 4 if level <= 1 else level - 1
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        level = 1 if level >= 4 else level + 1
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        game_state = "playing"
                        init_level()
                else:
                    if event.key == pygame.K_ESCAPE:
                        game_state = "title"
                    elif event.key in (pygame.K_UP, pygame.K_SPACE, pygame.K_w):
                        player.jump()
                    elif event.key == pygame.K_r:
                        init_level()

        if game_state == "title":
            draw_title_screen(screen, world, level)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # Continuous Input (playing only; locked during flag-clear slide)
        keys = pygame.key.get_pressed()
        if not player.is_dead and not level_clearing:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: player.vel_x = -PLAYER_SPEED
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: player.vel_x = PLAYER_SPEED
            else: player.vel_x = 0
        elif level_clearing:
            player.vel_x = 0

        # Prevent moving left past start of level
        if player.rect.left < 0:
            player.rect.left = 0
            player.vel_x = max(0.0, player.vel_x)

        # 2. Update Physics
        # Flagpole (F top + | pole) is non-solid; player overlaps to trigger the flag.
        flag_types = ("F", "|")
        solid_rects = [t["rect"] for t in tiles if t["type"] not in flag_types]
        # Wider flag trigger so pole side-touch always overlaps
        flag_rects = [t["rect"].inflate(8, 0) for t in tiles if t["type"] in flag_types]

        player.update(solid_rects)

        for enemy in enemies:
            enemy.update(solid_rects)
            if enemy.is_active and not player.is_dead and not level_clearing and player.rect.colliderect(enemy.rect):
                if player.vel_y > 0 and player.rect.bottom < enemy.rect.centery:
                    enemy.is_active = False
                    player.vel_y = JUMP_FORCE * 0.7
                    player.is_jumping = True
                else:
                    player.is_dead = True
                    player.vel_y = JUMP_FORCE

        # Flag / pole touch → enter level-clear state for ~1s, then advance.
        if not player.is_dead and not level_clearing:
            if any(player.rect.colliderect(fr) for fr in flag_rects):
                level_clearing = True
                clear_timer = 60

        if level_clearing:
            clear_timer -= 1
            if clear_timer <= 0:
                level += 1
                if level > 4:
                    level = 1
                    world += 1
                if world > 8:
                    world = 1
                init_level()

        # Respawn if fallen entirely off-screen
        if not level_clearing and player.rect.top > SCREEN_HEIGHT:
            init_level()

        # 3. Camera Tracking
        if not player.is_dead:
            target_camera_x = player.rect.x - SCREEN_WIDTH // 3
            if target_camera_x > camera_x: 
                camera_x = target_camera_x
            
            max_camera_x = level_width_pixels - SCREEN_WIDTH
            if camera_x > max_camera_x: camera_x = max_camera_x
            if camera_x < 0: camera_x = 0

        # 4. Rendering
        screen.fill(current_sky_color)

        # Draw Static Tiles (Visible only)
        for tile in tiles:
            t_rect = tile["rect"]
            if t_rect.right > camera_x and t_rect.left < camera_x + SCREEN_WIDTH:
                draw_rect = t_rect.copy()
                draw_rect.x -= camera_x
                ttype = tile["type"]
                if ttype == "F":
                    _draw_flagpole_tile(screen, draw_rect, is_top=True)
                elif ttype == "|":
                    _draw_flagpole_tile(screen, draw_rect, is_top=False)
                elif ttype in ("G", "B", "Q", "P", "S"):
                    _draw_tile_smb1(screen, draw_rect, ttype, tile.get("gx", 0), tile.get("gy", 0))
                else:
                    color = tile_colors.get(ttype, (128, 128, 128))
                    pygame.draw.rect(screen, color, draw_rect)
                    pygame.draw.rect(screen, SMB1_BLACK, draw_rect, 1)

        # Draw Entities
        for enemy in enemies:
            enemy.draw(screen, int(camera_x))
            
        player.draw(screen, int(camera_x))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()