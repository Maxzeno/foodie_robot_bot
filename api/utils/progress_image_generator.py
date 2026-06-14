"""
Progress Image Generator for shareable WhatsApp status images.
Generates beautifully branded progress cards with streak, calories, and leaderboard info.
"""
import io
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional, List, Tuple
import cloudinary.uploader


# Brand colors - FoodieRobot yellow/gold theme (refined)
COLORS = {
    'background': '#FEF9EF',       # Warm cream background
    'background_alt': '#FFF5E1',   # Slightly darker cream for contrast
    'card_bg': '#FFFFFF',          # Pure white cards
    'primary': '#FFBF00',          # FoodieRobot yellow/gold
    'primary_light': '#FFD54F',    # Lighter gold
    'primary_dark': '#E5AB00',     # Darker gold
    'secondary': '#1E1E2F',        # Rich dark navy
    'accent': '#FF6B35',           # Vibrant orange for highlights
    'accent_light': '#FF8A5C',     # Lighter orange
    'text_dark': '#1E1E2F',        # Dark text
    'text_medium': '#4A4A5A',      # Medium gray text
    'text_light': '#8A8A9A',       # Light gray text
    'text_white': '#FFFFFF',
    'gold': '#FFD700',
    'gold_dark': '#DAA520',
    'silver': '#B8C4CE',
    'bronze': '#CD8052',
    'success': '#34C759',          # iOS green
    'warning': '#FF9500',          # iOS orange
    'progress_bg': '#F0F0F5',      # Light gray progress bg
    'shadow': '#1E1E2F',           # Shadow color
    'border': '#E8E8ED',           # Light border
}

# Image dimensions (optimized for WhatsApp status - 9:16 aspect ratio)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get font with fallback to default."""
    try:
        # TODO: look into
        font_paths = [
            # macOS fonts
            "/System/Library/Fonts/SFNSDisplay.ttf" if bold else "/System/Library/Fonts/SFNSText.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
            # Linux fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Windows fonts
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _draw_shadow_rectangle(
    draw: ImageDraw.ImageDraw,
    coords: Tuple[int, int, int, int],
    radius: int,
    fill: str,
    shadow_offset: int = 6,
    shadow_opacity: str = '#00000012'
):
    """Draw a rounded rectangle with soft shadow."""
    x1, y1, x2, y2 = coords
    # Shadow
    draw.rounded_rectangle(
        (x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
        radius=radius,
        fill=shadow_opacity
    )
    # Main rectangle
    draw.rounded_rectangle(coords, radius=radius, fill=fill)


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    percentage: float,
    bg_color: str,
    fill_color: str,
    show_glow: bool = True
):
    """Draw a modern progress bar with rounded ends."""
    # Background
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=height // 2,
        fill=bg_color
    )
    # Fill
    fill_width = int(width * min(percentage / 100, 1))
    if fill_width > height:  # Ensure minimum width for rounded corners
        draw.rounded_rectangle(
            (x, y, x + fill_width, y + height),
            radius=height // 2,
            fill=fill_color
        )


def _draw_robot_mascot(draw: ImageDraw.ImageDraw, x: int, y: int, size: int):
    """Draw an improved FoodieRobot mascot."""
    head_width = size
    head_height = int(size * 0.8)

    # Antenna stem
    antenna_height = size // 3
    antenna_width = size // 12
    draw.rounded_rectangle(
        (x - antenna_width // 2, y - antenna_height + 10, x + antenna_width // 2, y + 5),
        radius=antenna_width // 2,
        fill=COLORS['primary']
    )

    # Antenna balls (two small ones)
    ball_radius = size // 10
    # Left antenna
    draw.ellipse(
        (x - size // 5 - ball_radius, y - antenna_height - ball_radius,
         x - size // 5 + ball_radius, y - antenna_height + ball_radius),
        fill=COLORS['primary']
    )
    draw.line(
        (x - size // 5, y - antenna_height + ball_radius, x - antenna_width // 4, y),
        fill=COLORS['primary'],
        width=antenna_width
    )
    # Right antenna
    draw.ellipse(
        (x + size // 5 - ball_radius, y - antenna_height - ball_radius,
         x + size // 5 + ball_radius, y - antenna_height + ball_radius),
        fill=COLORS['primary']
    )
    draw.line(
        (x + size // 5, y - antenna_height + ball_radius, x + antenna_width // 4, y),
        fill=COLORS['primary'],
        width=antenna_width
    )

    # Robot head with slight shadow
    draw.rounded_rectangle(
        (x - head_width // 2 + 4, y + 4, x + head_width // 2 + 4, y + head_height + 4),
        radius=size // 4,
        fill='#00000015'
    )
    draw.rounded_rectangle(
        (x - head_width // 2, y, x + head_width // 2, y + head_height),
        radius=size // 4,
        fill=COLORS['primary']
    )

    # Eyes - larger, more expressive
    eye_size = size // 4
    eye_y = y + head_height // 2.5
    left_eye_x = x - size // 4
    right_eye_x = x + size // 4

    # Eye whites with slight shadow
    draw.ellipse(
        (left_eye_x - eye_size + 2, eye_y - eye_size + 2, left_eye_x + eye_size + 2, eye_y + eye_size + 2),
        fill='#00000010'
    )
    draw.ellipse(
        (left_eye_x - eye_size, eye_y - eye_size, left_eye_x + eye_size, eye_y + eye_size),
        fill=COLORS['text_white']
    )
    draw.ellipse(
        (right_eye_x - eye_size + 2, eye_y - eye_size + 2, right_eye_x + eye_size + 2, eye_y + eye_size + 2),
        fill='#00000010'
    )
    draw.ellipse(
        (right_eye_x - eye_size, eye_y - eye_size, right_eye_x + eye_size, eye_y + eye_size),
        fill=COLORS['text_white']
    )

    # Pupils - looking slightly to the side for personality
    pupil_size = eye_size // 2
    pupil_offset = 2
    draw.ellipse(
        (left_eye_x - pupil_size + pupil_offset, eye_y - pupil_size,
         left_eye_x + pupil_size + pupil_offset, eye_y + pupil_size),
        fill=COLORS['secondary']
    )
    draw.ellipse(
        (right_eye_x - pupil_size + pupil_offset, eye_y - pupil_size,
         right_eye_x + pupil_size + pupil_offset, eye_y + pupil_size),
        fill=COLORS['secondary']
    )

    # Eye shine
    shine_size = pupil_size // 2
    draw.ellipse(
        (left_eye_x - shine_size + pupil_offset + 3, eye_y - pupil_size + 2,
         left_eye_x + shine_size + pupil_offset + 3, eye_y - pupil_size + 2 + shine_size),
        fill=COLORS['text_white']
    )
    draw.ellipse(
        (right_eye_x - shine_size + pupil_offset + 3, eye_y - pupil_size + 2,
         right_eye_x + shine_size + pupil_offset + 3, eye_y - pupil_size + 2 + shine_size),
        fill=COLORS['text_white']
    )

    # Happy smile
    smile_y = y + head_height * 0.72
    smile_width = size // 2.5
    draw.arc(
        (x - smile_width, smile_y - smile_width // 2, x + smile_width, smile_y + smile_width // 2),
        start=10, end=170,
        fill=COLORS['secondary'],
        width=max(size // 12, 4)
    )


def _draw_decorative_elements(draw: ImageDraw.ImageDraw, width: int, height: int, seed: int = 42):
    """Draw subtle decorative dots and shapes."""
    import random
    random.seed(seed)

    # Subtle dots scattered around
    dot_colors = [COLORS['primary_light'], COLORS['accent_light'], '#FFE4B5', '#FFA07A']

    positions = [
        (80, 120), (width - 100, 150), (120, height - 200),
        (width - 80, height - 180), (width // 2 - 200, 200),
        (width // 2 + 220, 180), (90, height // 2),
        (width - 90, height // 2 + 100), (200, height - 100),
    ]

    for px, py in positions:
        size = random.randint(12, 24)
        color = random.choice(dot_colors)
        draw.ellipse((px, py, px + size, py + size), fill=color)


def _draw_rank_badge(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    rank: int,
    size: int = 50
):
    """Draw a circular rank badge."""
    colors = {
        1: (COLORS['gold'], COLORS['gold_dark']),
        2: (COLORS['silver'], '#9AA5AF'),
        3: (COLORS['bronze'], '#B86B3A'),
    }

    fill_color, border_color = colors.get(rank, (COLORS['text_light'], COLORS['text_medium']))

    # Badge circle with border effect
    draw.ellipse(
        (x - size // 2 - 3, y - size // 2 - 3, x + size // 2 + 3, y + size // 2 + 3),
        fill=border_color
    )
    draw.ellipse(
        (x - size // 2, y - size // 2, x + size // 2, y + size // 2),
        fill=fill_color
    )


def generate_progress_image(
    day_number: int,
    streak: int,
    calories_consumed: int,
    calories_target: int,
    leaderboard: List[dict],
    user_rank: Optional[int],
    user_orders: int,
    month_name: str,
    brand_name: str = "FoodieRobot"
) -> bytes:
    """
    Generate a beautiful, shareable progress image.

    Returns:
        bytes: PNG image data
    """
    # Create image with warm background
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), COLORS['background'])
    draw = ImageDraw.Draw(img)

    # Add subtle decorative elements
    _draw_decorative_elements(draw, IMAGE_WIDTH, IMAGE_HEIGHT)

    # Fonts
    font_brand = _get_font(56, bold=True)
    font_section_title = _get_font(36, bold=True)
    font_day_number = _get_font(160, bold=True)
    font_day_label = _get_font(32, bold=False)
    font_large = _get_font(44, bold=True)
    font_medium = _get_font(38, bold=False)
    font_medium_bold = _get_font(38, bold=True)
    font_small = _get_font(30, bold=False)
    font_streak = _get_font(36, bold=True)
    font_cta = _get_font(40, bold=True)
    font_footer = _get_font(28, bold=False)

    y_cursor = 70
    card_margin = 60
    card_padding = 40
    card_radius = 32

    # ===== HEADER: Robot + Brand =====
    _draw_robot_mascot(draw, IMAGE_WIDTH // 2, y_cursor + 30, 130)
    y_cursor += 190

    # Brand name with subtle styling
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor),
        brand_name,
        font=font_brand,
        fill=COLORS['secondary'],
        anchor="mt"
    )
    y_cursor += 85

    # ===== MAIN CARD: Day Journey =====
    card_top = y_cursor
    card_height = 380

    _draw_shadow_rectangle(
        draw,
        (card_margin, card_top, IMAGE_WIDTH - card_margin, card_top + card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Accent line at top
    draw.rounded_rectangle(
        (card_margin, card_top, IMAGE_WIDTH - card_margin, card_top + 8),
        radius=4,
        fill=COLORS['primary']
    )

    # Section label
    draw.text(
        (IMAGE_WIDTH // 2, card_top + 45),
        "MY JOURNEY",
        font=font_section_title,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Big DAY number
    draw.text(
        (IMAGE_WIDTH // 2, card_top + 85),
        f"DAY {day_number}",
        font=font_day_number,
        fill=COLORS['primary'],
        anchor="mt"
    )

    # Streak badge
    if streak > 1:
        streak_y = card_top + 280
        badge_width = 320
        badge_x = (IMAGE_WIDTH - badge_width) // 2
        badge_color = COLORS['accent'] if streak >= 7 else COLORS['primary']

        # Badge with slight shadow
        draw.rounded_rectangle(
            (badge_x + 3, streak_y + 3, badge_x + badge_width + 3, streak_y + 60 + 3),
            radius=30,
            fill='#00000015'
        )
        draw.rounded_rectangle(
            (badge_x, streak_y, badge_x + badge_width, streak_y + 60),
            radius=30,
            fill=badge_color
        )

        streak_emoji = "🔥" if streak >= 7 else "⚡"
        draw.text(
            (IMAGE_WIDTH // 2, streak_y + 30),
            f"{streak_emoji} {streak}-day streak!",
            font=font_streak,
            fill=COLORS['text_white'],
            anchor="mm"
        )

    y_cursor = card_top + card_height + 30

    # ===== CALORIES CARD =====
    cal_card_height = 200

    _draw_shadow_rectangle(
        draw,
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + cal_card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Section title with icon
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 30),
        "🍽️  TODAY'S CALORIES",
        font=font_section_title,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Calorie numbers
    cal_percentage = (calories_consumed / calories_target * 100) if calories_target > 0 else 0

    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 80),
        f"{calories_consumed:,}",
        font=font_large,
        fill=COLORS['text_dark'],
        anchor="mt"
    )
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 125),
        f"of {calories_target:,} kcal",
        font=font_small,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Progress bar
    bar_margin = card_margin + card_padding
    bar_y = y_cursor + 165
    bar_height = 20

    # Determine color based on percentage
    if cal_percentage <= 75:
        bar_color = COLORS['success']
    elif cal_percentage <= 100:
        bar_color = COLORS['primary']
    else:
        bar_color = COLORS['warning']

    _draw_progress_bar(
        draw, bar_margin, bar_y, IMAGE_WIDTH - (bar_margin * 2), bar_height,
        cal_percentage, COLORS['progress_bg'], bar_color
    )

    # Percentage on right
    draw.text(
        (IMAGE_WIDTH - bar_margin + 10, bar_y + bar_height // 2),
        f"{min(cal_percentage, 100):.0f}%",
        font=font_small,
        fill=COLORS['text_medium'],
        anchor="lm"
    )

    y_cursor += cal_card_height + 30

    # ===== LEADERBOARD CARD =====
    lb_card_height = 380

    _draw_shadow_rectangle(
        draw,
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + lb_card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Section title
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 30),
        f"🏆  {month_name.upper()} LEADERBOARD",
        font=font_section_title,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Leaderboard entries
    entry_start_y = y_cursor + 85
    entry_height = 75

    if leaderboard:
        for idx, entry in enumerate(leaderboard[:3]):
            entry_y = entry_start_y + (idx * entry_height)
            name = entry.get('name', 'Unknown')
            orders = entry.get('orders', 0)
            is_user = entry.get('is_user', False)

            # Row background for user
            if is_user:
                draw.rounded_rectangle(
                    (card_margin + 20, entry_y - 5, IMAGE_WIDTH - card_margin - 20, entry_y + entry_height - 15),
                    radius=16,
                    fill='#FFF3E0'
                )

            # Rank badge
            badge_x = card_margin + 70
            _draw_rank_badge(draw, badge_x, entry_y + 25, idx + 1, size=46)

            # Rank number on badge
            rank_font = _get_font(24, bold=True)
            draw.text(
                (badge_x, entry_y + 25),
                str(idx + 1),
                font=rank_font,
                fill=COLORS['text_white'] if idx < 2 else COLORS['text_dark'],
                anchor="mm"
            )

            # Name
            name_color = COLORS['accent'] if is_user else COLORS['text_dark']
            display_name = name + (" 👈" if is_user else "")
            draw.text(
                (card_margin + 120, entry_y + 25),
                display_name,
                font=font_medium_bold if is_user else font_medium,
                fill=name_color,
                anchor="lm"
            )

            # Orders count
            draw.text(
                (IMAGE_WIDTH - card_margin - 40, entry_y + 25),
                f"{orders}",
                font=font_medium_bold,
                fill=COLORS['text_medium'],
                anchor="rm"
            )
            draw.text(
                (IMAGE_WIDTH - card_margin - 40, entry_y + 55),
                "orders",
                font=font_small,
                fill=COLORS['text_light'],
                anchor="rm"
            )

        # User rank if not in top 3
        if user_rank and user_rank > 3:
            rank_y = entry_start_y + (3 * entry_height) + 10
            draw.text(
                (IMAGE_WIDTH // 2, rank_y),
                f"Your rank: #{user_rank}",
                font=font_medium,
                fill=COLORS['accent'],
                anchor="mt"
            )
    else:
        # Empty state
        empty_y = entry_start_y + 80
        draw.text(
            (IMAGE_WIDTH // 2, empty_y),
            "No rankings yet",
            font=font_medium,
            fill=COLORS['text_light'],
            anchor="mt"
        )
        draw.text(
            (IMAGE_WIDTH // 2, empty_y + 50),
            "Order to claim the top spot! 🚀",
            font=font_medium,
            fill=COLORS['primary'],
            anchor="mt"
        )

    y_cursor += lb_card_height + 35

    # ===== CTA BUTTON =====
    cta_height = 80

    # Button shadow
    draw.rounded_rectangle(
        (card_margin + 4, y_cursor + 4, IMAGE_WIDTH - card_margin + 4, y_cursor + cta_height + 4),
        radius=cta_height // 2,
        fill='#00000020'
    )
    draw.rounded_rectangle(
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + cta_height),
        radius=cta_height // 2,
        fill=COLORS['primary']
    )

    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + cta_height // 2),
        "Share your progress! 🎉",
        font=font_cta,
        fill=COLORS['text_white'],
        anchor="mm"
    )

    # ===== FOOTER =====
    draw.text(
        (IMAGE_WIDTH // 2, IMAGE_HEIGHT - 50),
        "foodierobot.com",
        font=font_footer,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG', optimize=True, quality=95)
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()


def upload_progress_image(image_bytes: bytes, user_code: str) -> Optional[str]:
    try:
        filename = f"progress_{user_code}_{uuid.uuid4().hex[:8]}"

        result = cloudinary.uploader.upload(
            image_bytes,
            folder="progress_cards",
            public_id=filename,
            resource_type="image",
            format="png",
            invalidate=True,
        )

        return result.get('secure_url')

    except Exception as e:
        print(f"Error uploading progress image: {e}")
        return None
