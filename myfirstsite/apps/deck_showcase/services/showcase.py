import io
import math
from collections import Counter
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
# Tech-frame background with deck color adaptation
# ============================================================

# WS four-color palettes
WS_COLOR_PALETTES = {
    'red':    {'base': (40, 12, 15), 'accent': (180, 50, 60),  'glow': (220, 80, 90)},
    'blue':   {'base': (12, 18, 42), 'accent': (50, 100, 180), 'glow': (80, 140, 220)},
    'yellow': {'base': (38, 30, 12), 'accent': (180, 150, 50), 'glow': (220, 190, 80)},
    'green':  {'base': (12, 35, 18), 'accent': (50, 160, 80),  'glow': (80, 200, 110)},
}

# Default palette when color cannot be determined
_DEFAULT_PALETTE = {'base': (20, 18, 30), 'accent': (100, 80, 140), 'glow': (150, 120, 190)}


def _count_deck_colors(cards):
    """Count card colors and return the dominant color name."""
    counts = Counter()
    for c in cards:
        color = (c.get('color') or '').lower().strip()
        if color in WS_COLOR_PALETTES:
            counts[color] += 1
    if not counts:
        return 'blue'  # fallback
    return counts.most_common(1)[0][0]


def _create_tech_background(dominant_color='blue'):
    """Create a fixed tech-frame background with color adapted to deck."""
    palette = WS_COLOR_PALETTES.get(dominant_color, _DEFAULT_PALETTE)
    base = palette['base']
    accent = palette['accent']
    glow = palette['glow']

    canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Gradient base (top lighter, bottom darker)
    for y in range(CANVAS_H):
        ratio = y / CANVAS_H
        r = int(base[0] + 12 * (1 - ratio))
        g = int(base[1] + 10 * (1 - ratio))
        b = int(base[2] + 8 * (1 - ratio))
        draw.line([(0, y), (CANVAS_W, y)], fill=(r, g, b, 255))

    # 2. Center glow (soft radial light)
    glow_overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    cx, cy = CANVAS_W // 2, CANVAS_H // 2
    for radius in range(300, 0, -5):
        alpha = int(18 * (1 - radius / 300))
        glow_draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*glow, alpha),
        )
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(50))
    canvas = Image.alpha_composite(canvas, glow_overlay)

    draw = ImageDraw.Draw(canvas)

    # 3. Double-frame border
    m1 = 16  # outer margin
    m2 = 24  # inner margin
    draw.rectangle(
        [m1, m1, CANVAS_W - m1, CANVAS_H - m1],
        outline=(*accent, 70), width=2,
    )
    draw.rectangle(
        [m2, m2, CANVAS_W - m2, CANVAS_H - m2],
        outline=(*accent, 40), width=1,
    )

    # 4. Corner L-decorations
    corner_len = 40
    corner_color = (*accent, 100)
    corners = [
        # top-left
        ((m1, m1), (m1 + corner_len, m1), (m1, m1 + corner_len)),
        # top-right
        ((CANVAS_W - m1, m1), (CANVAS_W - m1 - corner_len, m1), (CANVAS_W - m1, m1 + corner_len)),
        # bottom-left
        ((m1, CANVAS_H - m1), (m1 + corner_len, CANVAS_H - m1), (m1, CANVAS_H - m1 - corner_len)),
        # bottom-right
        ((CANVAS_W - m1, CANVAS_H - m1), (CANVAS_W - m1 - corner_len, CANVAS_H - m1), (CANVAS_W - m1, CANVAS_H - m1 - corner_len)),
    ]
    for corner_pt, h_end, v_end in corners:
        draw.line([corner_pt, h_end], fill=corner_color, width=3)
        draw.line([corner_pt, v_end], fill=corner_color, width=3)

    # 5. Corner dots
    dot_r = 3
    dot_color = (*glow, 120)
    for x, y in [(m1, m1), (CANVAS_W - m1, m1), (m1, CANVAS_H - m1), (CANVAS_W - m1, CANVAS_H - m1)]:
        draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=dot_color)

    # 6. Scan lines (horizontal, faint)
    scan_overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(scan_overlay)
    for y in range(0, CANVAS_H, 4):
        s_draw.line([(0, y), (CANVAS_W, y)], fill=(*accent, 8))
    canvas = Image.alpha_composite(canvas, scan_overlay)

    # 7. Vertical accent lines at 1/4 and 3/4
    line_overlay = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    l_draw = ImageDraw.Draw(line_overlay)
    for x_pos in [CANVAS_W // 4, 3 * CANVAS_W // 4]:
        l_draw.line([(x_pos, m2 + 10), (x_pos, CANVAS_H - m2 - 10)], fill=(*accent, 15), width=1)
    canvas = Image.alpha_composite(canvas, line_overlay)

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
    Generate a deck showcase image with arch-down fan, tech-frame background,
    and optional player info.
    """
    # Determine dominant color from selected cards
    dominant_color = _count_deck_colors(selected_cards)

    # Collect image paths
    img_paths = set()
    for c in selected_cards:
        if c.get('img'):
            img_paths.add(c['img'])

    if not img_paths:
        return _generate_placeholder(deck_data, dominant_color)

    images = _download_all_images(img_paths)

    if not images:
        return _generate_placeholder(deck_data, dominant_color)

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

    # Create canvas with tech-frame background
    canvas = _create_tech_background(dominant_color)

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


def _generate_placeholder(deck_data, dominant_color='blue'):
    """Generate a simple placeholder image when no card images are available."""
    canvas = _create_tech_background(dominant_color)
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
