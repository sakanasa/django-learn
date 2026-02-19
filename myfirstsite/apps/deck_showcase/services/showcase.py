import io
import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Card image base URL
WS_TCG_IMG_BASE = 'https://ws-tcg.com/wordpress/wp-content/images/cardlist/'

# Output canvas size
CANVAS_W, CANVAS_H = 1200, 630

# Character card original size (portrait)
CHAR_W, CHAR_H = 400, 559

# CX card original size (landscape)
CX_W, CX_H = 559, 400

# Font fallback chain for CJK support
_FONT_PATHS = [
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/System/Library/Fonts/Helvetica.ttc',
]


def _load_font(size):
    """Load a font with CJK fallback chain."""
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _download_image(img_path):
    """Download a card image and return as PIL Image."""
    url = WS_TCG_IMG_BASE + img_path
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert('RGBA')
    except Exception:
        return None


def _download_all_images(img_paths):
    """Download multiple images concurrently. Returns dict of path -> Image."""
    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_download_image, p): p for p in img_paths}
        for future in as_completed(futures):
            path = futures[future]
            img = future.result()
            if img:
                results[path] = img
    return results


# ============================================================
# Themed backgrounds (Change 2)
# ============================================================

def _create_themed_background():
    """Create a random themed background canvas."""
    theme = random.choice(['ink_wash', 'ancient', 'cyber', 'gradient'])
    return {
        'ink_wash': _bg_ink_wash,
        'ancient': _bg_ancient,
        'cyber': _bg_cyber,
        'gradient': _bg_gradient,
    }[theme]()


def _bg_ink_wash():
    """Soft grey ink wash background with splatter effects."""
    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    # Base grey gradient
    for y in range(CANVAS_H):
        ratio = y / CANVAS_H
        v = int(35 + 15 * (1 - ratio))
        draw.line([(0, y), (CANVAS_W, y)], fill=(v, v, v + 3, 255))

    # Random semi-transparent ink splatters
    overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for _ in range(random.randint(6, 12)):
        cx = random.randint(-100, CANVAS_W + 100)
        cy = random.randint(-100, CANVAS_H + 100)
        r = random.randint(60, 250)
        tone = random.randint(20, 60)
        alpha = random.randint(30, 80)
        ov_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(tone, tone, tone, alpha),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(40))
    canvas = Image.alpha_composite(canvas, overlay)

    # Horizontal brush strokes
    stroke_overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stroke_overlay)
    for _ in range(random.randint(3, 7)):
        y = random.randint(0, CANVAS_H)
        tone = random.randint(40, 70)
        alpha = random.randint(15, 40)
        thickness = random.randint(2, 6)
        for dy in range(thickness):
            s_draw.line([(0, y + dy), (CANVAS_W, y + dy)],
                        fill=(tone, tone, tone, alpha))
    canvas = Image.alpha_composite(canvas, stroke_overlay)

    return canvas


def _bg_ancient():
    """Warm golden-brown ancient parchment background."""
    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    # Warm gradient from dark brown to amber
    for y in range(CANVAS_H):
        ratio = y / CANVAS_H
        r = int(40 + 25 * ratio)
        g = int(25 + 18 * ratio)
        b = int(15 + 8 * ratio)
        draw.line([(0, y), (CANVAS_W, y)], fill=(r, g, b, 255))

    # Decorative border lines
    border_color = (120, 85, 40, 80)
    margin = 20
    draw.rectangle(
        [margin, margin, CANVAS_W - margin, CANVAS_H - margin],
        outline=border_color, width=2,
    )
    draw.rectangle(
        [margin + 6, margin + 6, CANVAS_W - margin - 6, CANVAS_H - margin - 6],
        outline=(100, 70, 30, 50), width=1,
    )

    # Faint circular seal patterns
    overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for _ in range(random.randint(2, 5)):
        cx = random.randint(50, CANVAS_W - 50)
        cy = random.randint(50, CANVAS_H - 50)
        r = random.randint(30, 80)
        ov_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(140, 100, 50, 35), width=2,
        )
    canvas = Image.alpha_composite(canvas, overlay)

    return canvas


def _bg_cyber():
    """Dark blue cyber/tech background with grid and neon accents."""
    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (10, 10, 30, 255))
    draw = ImageDraw.Draw(canvas)

    # Subtle vertical gradient
    for y in range(CANVAS_H):
        ratio = y / CANVAS_H
        r = int(10 + 5 * ratio)
        g = int(10 + 5 * ratio)
        b = int(30 + 15 * (1 - ratio))
        draw.line([(0, y), (CANVAS_W, y)], fill=(r, g, b, 255))

    # Perspective grid lines
    grid_color = (30, 60, 100, 40)
    # Horizontal lines
    for y in range(0, CANVAS_H, 40):
        draw.line([(0, y), (CANVAS_W, y)], fill=grid_color, width=1)
    # Vertical lines converging
    vanish_x, vanish_y = CANVAS_W // 2, CANVAS_H // 3
    for x in range(0, CANVAS_W + 1, 80):
        draw.line([(x, CANVAS_H), (vanish_x, vanish_y)], fill=grid_color, width=1)

    # Random bright rectangles
    overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    neon_colors = [
        (0, 200, 255), (255, 0, 150), (0, 255, 100),
        (255, 200, 0), (150, 0, 255),
    ]
    for _ in range(random.randint(4, 10)):
        rx = random.randint(0, CANVAS_W)
        ry = random.randint(0, CANVAS_H)
        rw = random.randint(10, 60)
        rh = random.randint(10, 40)
        color = random.choice(neon_colors)
        alpha = random.randint(15, 40)
        ov_draw.rectangle([rx, ry, rx + rw, ry + rh], fill=(*color, alpha))

    # Neon glow circles
    for _ in range(random.randint(2, 5)):
        cx = random.randint(0, CANVAS_W)
        cy = random.randint(0, CANVAS_H)
        r = random.randint(40, 120)
        color = random.choice(neon_colors)
        ov_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*color, 15),
        )
    overlay = overlay.filter(ImageFilter.GaussianBlur(15))
    canvas = Image.alpha_composite(canvas, overlay)

    return canvas


def _bg_gradient():
    """Colorful diagonal/radial gradient with randomized palettes."""
    palettes = [
        [(15, 10, 35), (45, 20, 60), (80, 30, 90)],
        [(10, 20, 40), (20, 50, 80), (40, 80, 120)],
        [(30, 10, 20), (60, 20, 40), (100, 30, 60)],
        [(10, 30, 25), (20, 60, 50), (30, 90, 75)],
        [(25, 15, 40), (50, 30, 70), (90, 50, 100)],
        [(35, 15, 15), (70, 25, 25), (110, 40, 40)],
    ]
    palette = random.choice(palettes)
    use_radial = random.choice([True, False])

    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    if use_radial:
        # Radial gradient from center
        cx, cy = CANVAS_W // 2, CANVAS_H // 2
        max_dist = math.sqrt(cx ** 2 + cy ** 2)
        for y in range(CANVAS_H):
            for x in range(0, CANVAS_W, 4):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                ratio = min(dist / max_dist, 1.0)
                if ratio < 0.5:
                    t = ratio * 2
                    r = int(palette[0][0] + (palette[1][0] - palette[0][0]) * t)
                    g = int(palette[0][1] + (palette[1][1] - palette[0][1]) * t)
                    b = int(palette[0][2] + (palette[1][2] - palette[0][2]) * t)
                else:
                    t = (ratio - 0.5) * 2
                    r = int(palette[1][0] + (palette[2][0] - palette[1][0]) * t)
                    g = int(palette[1][1] + (palette[2][1] - palette[1][1]) * t)
                    b = int(palette[1][2] + (palette[2][2] - palette[1][2]) * t)
                draw.rectangle([x, y, x + 3, y], fill=(r, g, b, 255))
    else:
        # Diagonal gradient
        for y in range(CANVAS_H):
            for x in range(0, CANVAS_W, 4):
                ratio = (x / CANVAS_W + y / CANVAS_H) / 2
                if ratio < 0.5:
                    t = ratio * 2
                    r = int(palette[0][0] + (palette[1][0] - palette[0][0]) * t)
                    g = int(palette[0][1] + (palette[1][1] - palette[0][1]) * t)
                    b = int(palette[0][2] + (palette[1][2] - palette[0][2]) * t)
                else:
                    t = (ratio - 0.5) * 2
                    r = int(palette[1][0] + (palette[2][0] - palette[1][0]) * t)
                    g = int(palette[1][1] + (palette[2][1] - palette[1][1]) * t)
                    b = int(palette[1][2] + (palette[2][2] - palette[1][2]) * t)
                draw.rectangle([x, y, x + 3, y], fill=(r, g, b, 255))

    return canvas


# ============================================================
# Card rendering helpers
# ============================================================

def _add_drop_shadow(card_img, offset=8, blur_radius=15):
    """Add a drop shadow behind a card image."""
    shadow = Image.new('RGBA',
                       (card_img.width + blur_radius * 2 + offset,
                        card_img.height + blur_radius * 2 + offset),
                       (0, 0, 0, 0))
    shadow_layer = Image.new('RGBA', card_img.size, (0, 0, 0, 180))
    shadow.paste(shadow_layer, (blur_radius + offset, blur_radius + offset), card_img)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    shadow.paste(card_img, (blur_radius, blur_radius), card_img)
    return shadow


def _add_glow(card_img, color=(180, 130, 255), radius=8):
    """Add a subtle glow around the card."""
    glow_size = (card_img.width + radius * 4, card_img.height + radius * 4)
    glow = Image.new('RGBA', glow_size, (0, 0, 0, 0))
    glow_layer = Image.new('RGBA', card_img.size, (*color, 60))
    glow.paste(glow_layer, (radius * 2, radius * 2), card_img)
    glow = glow.filter(ImageFilter.GaussianBlur(radius * 2))
    glow.paste(card_img, (radius * 2, radius * 2), card_img)
    return glow


def _rotate_and_paste(canvas, card_img, center_x, center_y, angle):
    """Rotate a card image and paste it onto the canvas at the given center position."""
    rotated = card_img.rotate(angle, resample=Image.BICUBIC, expand=True)
    paste_x = center_x - rotated.width // 2
    paste_y = center_y - rotated.height // 2
    canvas.paste(rotated, (paste_x, paste_y), rotated)


def _draw_text_with_shadow(draw, pos, text, font, fill=(255, 255, 255, 220)):
    """Draw text with a dark shadow for readability."""
    x, y = pos
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=fill)


# ============================================================
# Fan layout (Change 1: arch-down)
# ============================================================

def _compute_fan_params(n):
    """Compute fan spread angles, scales, x-offsets, and y-offsets for n cards.

    Returns (angles, scales, offsets_x, offsets_y).
    Angles are negated so the fan arches downward (edges tilt inward, center lowest).
    Y-offsets use a parabola so edge cards rise and center card dips = more card face visible.
    """
    if n == 1:
        return [0], [1.0], [0], [0]

    # Arc depth for y-offset parabola (center card goes down by this many px)
    arc_depth = 30

    def _make_offsets_y(n):
        return [int(arc_depth * (1 - ((2 * i / (n - 1)) - 1) ** 2)) for i in range(n)]

    if n == 2:
        return [8, -8], [1.0, 1.0], [-90, 90], _make_offsets_y(2)
    elif n == 3:
        return [12, 0, -12], [0.9, 1.0, 0.9], [-170, 0, 170], _make_offsets_y(3)
    elif n == 4:
        return [16, 6, -6, -16], [0.85, 0.95, 0.95, 0.85], [-240, -80, 80, 240], _make_offsets_y(4)
    elif n == 5:
        return (
            [18, 9, 0, -9, -18],
            [0.80, 0.90, 1.0, 0.90, 0.80],
            [-300, -150, 0, 150, 300],
            _make_offsets_y(5),
        )
    elif n == 6:
        return (
            [20, 12, 4, -4, -12, -20],
            [0.78, 0.85, 0.95, 0.95, 0.85, 0.78],
            [-350, -210, -70, 70, 210, 350],
            _make_offsets_y(6),
        )
    elif n == 7:
        return (
            [21, 14, 7, 0, -7, -14, -21],
            [0.75, 0.82, 0.90, 1.0, 0.90, 0.82, 0.75],
            [-390, -260, -130, 0, 130, 260, 390],
            _make_offsets_y(7),
        )
    else:
        # 8+ cards: spread evenly
        step_angle = min(6, 42 / (n - 1))
        step_x = min(120, (CANVAS_W - 200) / (n - 1))
        half = (n - 1) / 2
        # Negate angles for arch-down
        angles = [round(-(i - half) * step_angle) for i in range(n)]
        scales = [max(0.7, 1.0 - abs(i - half) * 0.04) for i in range(n)]
        offsets_x = [round((i - half) * step_x) for i in range(n)]
        offsets_y = _make_offsets_y(n)
        return angles, scales, offsets_x, offsets_y


def _render_fan(canvas, card_imgs, center_x, center_y, center_idx):
    """Render character/event cards in a fan spread (arch-down orientation)."""
    n = len(card_imgs)
    if n == 0:
        return

    angles, scales, offsets_x, offsets_y = _compute_fan_params(n)

    # Draw edges first, center last (on top)
    draw_order = sorted(range(n), key=lambda i: -abs(angles[i]))

    for i in draw_order:
        img = card_imgs[i]
        s = scales[i]
        if s != 1.0:
            img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)

        # Center card gets glow, others get shadow
        if i == center_idx or n == 1:
            img = _add_glow(img, color=(242, 167, 195), radius=6)
        else:
            img = _add_drop_shadow(img, offset=5, blur_radius=10)

        cx = center_x + offsets_x[i]
        cy = center_y + offsets_y[i]
        _rotate_and_paste(canvas, img, cx, cy, angles[i])


def _render_cx_row(canvas, card_imgs, center_x, center_y):
    """Render CX cards in a horizontal row."""
    n = len(card_imgs)
    if n == 0:
        return

    spacing = 12
    total_w = sum(img.width for img in card_imgs) + spacing * (n - 1)
    start_x = center_x - total_w // 2

    cur_x = start_x
    for img in card_imgs:
        img_with_shadow = _add_drop_shadow(img, offset=4, blur_radius=8)
        paste_x = cur_x - (img_with_shadow.width - img.width) // 2
        paste_y = center_y - img_with_shadow.height // 2
        canvas.paste(img_with_shadow, (paste_x, paste_y), img_with_shadow)
        cur_x += img.width + spacing


# ============================================================
# Main generation function (Changes 1, 2, 3)
# ============================================================

def generate_showcase_image(selected_cards, deck_data,
                            player_name='', player_message=''):
    """
    Generate a deck showcase image with arch-down fan, themed background,
    and optional player info.
    """
    # Collect image paths
    img_paths = set()
    for c in selected_cards:
        if c.get('img'):
            img_paths.add(c['img'])

    if not img_paths:
        return _generate_placeholder(deck_data)

    images = _download_all_images(img_paths)

    if not images:
        return _generate_placeholder(deck_data)

    # Split into char/event cards and CX cards, prepare scaled images
    char_scale = 0.42
    cx_scale = 0.38
    char_imgs = []
    cx_imgs = []

    for c in selected_cards:
        if not c.get('img') or c['img'] not in images:
            continue
        img = images[c['img']].copy()
        if c.get('level') == 'CX':
            new_w = int(CX_W * cx_scale)
            new_h = int(CX_H * cx_scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            cx_imgs.append(img)
        else:
            new_w = int(CHAR_W * char_scale)
            new_h = int(CHAR_H * char_scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            char_imgs.append(img)

    if not char_imgs and not cx_imgs:
        return _generate_placeholder(deck_data)

    # Create canvas with random themed background
    canvas = _create_themed_background()

    has_char = len(char_imgs) > 0
    has_cx = len(cx_imgs) > 0

    # Determine center positions based on what's present
    if has_char and has_cx:
        fan_center_y = 235  # slightly lower to accommodate arch-down
        cx_center_y = 490
    elif has_char:
        fan_center_y = CANVAS_H // 2 - 15
        cx_center_y = 0
    else:
        fan_center_y = 0
        cx_center_y = CANVAS_H // 2

    fan_center_x = CANVAS_W // 2

    # Render character/event cards as fan
    if has_char:
        char_center_idx = len(char_imgs) // 2
        _render_fan(canvas, char_imgs, fan_center_x, fan_center_y, char_center_idx)

    # Render CX cards as horizontal row
    if has_cx:
        _render_cx_row(canvas, cx_imgs, fan_center_x, cx_center_y)

    # --- Bottom text overlay ---
    draw = ImageDraw.Draw(canvas)

    # Bottom gradient bar
    for y in range(CANVAS_H - 60, CANVAS_H):
        alpha = int(200 * ((y - (CANVAS_H - 60)) / 60))
        draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))

    font_large = _load_font(18)
    font_small = _load_font(14)
    font_tiny = _load_font(12)

    series_name = deck_data.get('series_name', '')
    deck_code = deck_data.get('deck_code', '')

    # Left side: series name (top line)
    if series_name:
        _draw_text_with_shadow(draw, (20, 575), series_name, font_large)

    # Left side: player info (bottom line)
    if player_name or player_message:
        player_text = player_name
        if player_message:
            player_text = f'{player_name}: {player_message}' if player_name else player_message
        # Truncate if too wide
        bbox = draw.textbbox((0, 0), player_text, font=font_tiny)
        max_w = CANVAS_W - 250  # leave room for deck code on right
        if (bbox[2] - bbox[0]) > max_w:
            while len(player_text) > 1:
                player_text = player_text[:-1]
                bbox = draw.textbbox((0, 0), player_text + '...', font=font_tiny)
                if (bbox[2] - bbox[0]) <= max_w:
                    break
            player_text += '...'
        _draw_text_with_shadow(
            draw, (20, 602), player_text, font_tiny,
            fill=(200, 200, 200, 200),
        )

    # Right side: deck code
    if deck_code:
        code_text = f'Code: {deck_code}'
        bbox = draw.textbbox((0, 0), code_text, font=font_small)
        code_w = bbox[2] - bbox[0]
        _draw_text_with_shadow(
            draw, (CANVAS_W - code_w - 20, 585),
            code_text, font_small,
            fill=(168, 216, 234, 220),
        )

    output = canvas.convert('RGB')
    buf = io.BytesIO()
    output.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _generate_placeholder(deck_data):
    """Generate a simple placeholder image when no card images are available."""
    canvas = _create_themed_background()
    draw = ImageDraw.Draw(canvas)

    font = _load_font(24)

    text = deck_data.get('series_name', 'Deck Showcase')
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    _draw_text_with_shadow(
        draw, ((CANVAS_W - tw) // 2, CANVAS_H // 2 - 12),
        text, font
    )

    output = canvas.convert('RGB')
    buf = io.BytesIO()
    output.save(buf, format='PNG', optimize=True)
    return buf.getvalue()
