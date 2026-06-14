"""
Progress Image Generator for shareable WhatsApp status images.
Generates beautifully branded progress cards with streak, calories, and leaderboard info.
"""
import io
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, List, Tuple
import cloudinary.uploader


# Brand colors - FoodieRobot yellow/gold theme (refined)
COLORS = {
    'background': '#FEF9EF',       # Warm cream background
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
    'progress_bg': '#E8E8ED',      # Light gray progress bg
}

# Image dimensions (optimized for WhatsApp status - 9:16 aspect ratio)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920

# Path to assets
ASSETS_PATH = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_PATH = os.path.join(ASSETS_PATH, 'logo.png')


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get font with fallback to default."""
    try:
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


def _draw_rounded_rect_with_shadow(
    draw: ImageDraw.ImageDraw,
    coords: Tuple[int, int, int, int],
    radius: int,
    fill: str,
    shadow_offset: int = 8,
):
    """Draw a rounded rectangle with soft shadow."""
    x1, y1, x2, y2 = coords
    # Shadow (subtle)
    draw.rounded_rectangle(
        (x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset),
        radius=radius,
        fill='#00000015'
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
    if fill_width > height:
        draw.rounded_rectangle(
            (x, y, x + fill_width, y + height),
            radius=height // 2,
            fill=fill_color
        )


def _draw_logo(img: Image.Image, x: int, y: int, width: int):
    """Draw the FoodieRobot logo on the image."""
    try:
        logo = Image.open(LOGO_PATH)

        # Resize logo while maintaining aspect ratio
        logo_ratio = logo.width / logo.height
        new_width = width
        new_height = int(width / logo_ratio)
        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate position to center the logo
        paste_x = x - new_width // 2
        paste_y = y

        # Handle transparency
        if logo.mode == 'RGBA':
            img.paste(logo, (paste_x, paste_y), logo)
        else:
            img.paste(logo, (paste_x, paste_y))

        return new_height
    except FileNotFoundError:
        print(f"Logo not found at {LOGO_PATH}")
        return 100


def _draw_decorative_dots(draw: ImageDraw.ImageDraw, width: int, height: int):
    """Draw subtle decorative dots."""
    import random
    random.seed(42)

    dot_colors = [COLORS['primary_light'], COLORS['accent_light'], '#FFE4B5']
    positions = [
        (60, 80), (width - 80, 120), (100, height - 150),
        (width - 60, height - 130), (width // 2 - 180, 160),
        (width // 2 + 200, 140), (70, height // 2 - 100),
        (width - 70, height // 2 + 80),
    ]

    for px, py in positions:
        size = random.randint(14, 28)
        color = random.choice(dot_colors)
        draw.ellipse((px, py, px + size, py + size), fill=color)


def _draw_rank_medal(draw: ImageDraw.ImageDraw, x: int, y: int, rank: int, size: int = 50):
    """Draw a circular rank medal."""
    colors = {
        1: (COLORS['gold'], COLORS['gold_dark']),
        2: (COLORS['silver'], '#9AA5AF'),
        3: (COLORS['bronze'], '#B86B3A'),
    }

    fill_color, border_color = colors.get(rank, (COLORS['text_light'], COLORS['text_medium']))

    # Outer border
    draw.ellipse(
        (x - size // 2 - 3, y - size // 2 - 3, x + size // 2 + 3, y + size // 2 + 3),
        fill=border_color
    )
    # Inner circle
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
    city_name: str,
) -> bytes:
    """
    Generate a beautiful, shareable progress image.
    """
    # Create image with warm background
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), COLORS['background'])
    draw = ImageDraw.Draw(img)

    # Add decorative dots
    _draw_decorative_dots(draw, IMAGE_WIDTH, IMAGE_HEIGHT)

    # Fonts
    font_section = _get_font(34, bold=True)
    font_day_big = _get_font(140, bold=True)
    font_large = _get_font(48, bold=True)
    font_medium = _get_font(36, bold=False)
    font_medium_bold = _get_font(36, bold=True)
    font_small = _get_font(28, bold=False)
    font_streak = _get_font(34, bold=True)
    font_cta = _get_font(38, bold=True)
    font_footer = _get_font(26, bold=False)

    # Layout constants
    card_margin = 50
    card_padding = 35
    card_radius = 28
    card_width = IMAGE_WIDTH - (card_margin * 2)

    y_cursor = 50

    # ===== LOGO =====
    logo_height = _draw_logo(img, IMAGE_WIDTH // 2, y_cursor, 480)
    y_cursor += logo_height + 40

    # ===== JOURNEY CARD =====
    journey_card_height = 340
    _draw_rounded_rect_with_shadow(
        draw,
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + journey_card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Top accent bar
    draw.rounded_rectangle(
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + 6),
        radius=3,
        fill=COLORS['primary']
    )

    # "MY JOURNEY" label
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 40),
        "MY JOURNEY",
        font=font_section,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Big DAY number
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 75),
        f"DAY {day_number}",
        font=font_day_big,
        fill=COLORS['primary'],
        anchor="mt"
    )

    # Streak badge (if streak > 1)
    if streak > 1:
        streak_y = y_cursor + 245
        badge_width = 280
        badge_x = (IMAGE_WIDTH - badge_width) // 2
        badge_color = COLORS['accent'] if streak >= 7 else COLORS['primary']

        # Badge shadow
        draw.rounded_rectangle(
            (badge_x + 3, streak_y + 3, badge_x + badge_width + 3, streak_y + 55 + 3),
            radius=28,
            fill='#00000012'
        )
        # Badge
        draw.rounded_rectangle(
            (badge_x, streak_y, badge_x + badge_width, streak_y + 55),
            radius=28,
            fill=badge_color
        )

        # Streak text (no emoji - using text instead)
        streak_icon = "***" if streak >= 7 else "*"
        draw.text(
            (IMAGE_WIDTH // 2, streak_y + 28),
            f"{streak_icon} {streak}-day streak! {streak_icon}",
            font=font_streak,
            fill=COLORS['text_white'],
            anchor="mm"
        )

    y_cursor += journey_card_height + 25

    # ===== CALORIES CARD =====
    cal_card_height = 180
    _draw_rounded_rect_with_shadow(
        draw,
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + cal_card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Section title
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 28),
        "TODAY'S CALORIES",
        font=font_section,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Calorie numbers
    cal_percentage = (calories_consumed / calories_target * 100) if calories_target > 0 else 0

    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 68),
        f"{calories_consumed:,}",
        font=font_large,
        fill=COLORS['text_dark'],
        anchor="mt"
    )
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 115),
        f"of {calories_target:,} kcal  ({min(cal_percentage, 100):.0f}%)",
        font=font_small,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Progress bar (inside card with proper margins)
    bar_x = card_margin + card_padding
    bar_width = card_width - (card_padding * 2)
    bar_y = y_cursor + 150
    bar_height = 16

    # Determine color based on percentage
    if cal_percentage <= 75:
        bar_color = COLORS['success']
    elif cal_percentage <= 100:
        bar_color = COLORS['primary']
    else:
        bar_color = COLORS['warning']

    _draw_progress_bar(
        draw, bar_x, bar_y, bar_width, bar_height,
        cal_percentage, COLORS['progress_bg'], bar_color
    )

    y_cursor += cal_card_height + 25

    # ===== LEADERBOARD CARD =====
    # Calculate height based on entries
    num_entries = min(len(leaderboard), 3) if leaderboard else 0
    entry_height = 70
    lb_card_height = 90 + (max(num_entries, 1) * entry_height) + 30

    if user_rank and user_rank > 3:
        lb_card_height += 50  # Extra space for "Your rank" text

    _draw_rounded_rect_with_shadow(
        draw,
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + lb_card_height),
        card_radius,
        COLORS['card_bg']
    )

    # Section title
    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + 28),
        f"{month_name.upper()} LEADERBOARD ({city_name})",
        font=font_section,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Leaderboard entries
    entry_start_y = y_cursor + 80

    if leaderboard:
        for idx, entry in enumerate(leaderboard[:3]):
            entry_y = entry_start_y + (idx * entry_height)
            name = entry.get('name', 'Unknown')
            orders = entry.get('orders', 0)
            is_user = entry.get('is_user', False)

            # Highlight row for user
            if is_user:
                draw.rounded_rectangle(
                    (card_margin + 15, entry_y - 8, IMAGE_WIDTH - card_margin - 15, entry_y + entry_height - 18),
                    radius=14,
                    fill='#FFF3E0'
                )

            # Rank medal
            badge_x = card_margin + 60
            _draw_rank_medal(draw, badge_x, entry_y + 25, idx + 1, size=44)

            # Rank number
            rank_font = _get_font(22, bold=True)
            rank_text_color = COLORS['text_white'] if idx < 2 else COLORS['text_dark']
            draw.text(
                (badge_x, entry_y + 25),
                str(idx + 1),
                font=rank_font,
                fill=rank_text_color,
                anchor="mm"
            )

            # Name
            name_color = COLORS['accent'] if is_user else COLORS['text_dark']
            display_name = name + (" (You)" if is_user else "")
            # Truncate long names
            if len(display_name) > 18:
                display_name = display_name[:16] + "..."
            draw.text(
                (card_margin + 105, entry_y + 25),
                display_name,
                font=font_medium_bold if is_user else font_medium,
                fill=name_color,
                anchor="lm"
            )

            # Orders count (right aligned, inside card)
            orders_x = IMAGE_WIDTH - card_margin - card_padding
            draw.text(
                (orders_x, entry_y + 18),
                f"{orders}",
                font=font_medium_bold,
                fill=COLORS['text_medium'],
                anchor="rm"
            )
            draw.text(
                (orders_x, entry_y + 48),
                "orders",
                font=font_small,
                fill=COLORS['text_light'],
                anchor="rm"
            )

        # User rank if not in top 3
        if user_rank and user_rank > 3:
            rank_y = entry_start_y + (num_entries * entry_height) + 10
            draw.text(
                (IMAGE_WIDTH // 2, rank_y),
                f"Your rank: #{user_rank} ({user_orders} orders)",
                font=font_medium,
                fill=COLORS['accent'],
                anchor="mt"
            )
    else:
        # Empty state
        empty_y = entry_start_y + 20
        draw.text(
            (IMAGE_WIDTH // 2, empty_y),
            "No rankings yet",
            font=font_medium,
            fill=COLORS['text_light'],
            anchor="mt"
        )
        draw.text(
            (IMAGE_WIDTH // 2, empty_y + 45),
            "Order to claim the top spot!",
            font=font_medium,
            fill=COLORS['primary'],
            anchor="mt"
        )

    y_cursor += lb_card_height + 30

    # ===== CTA BUTTON =====
    cta_height = 70

    # Button shadow
    draw.rounded_rectangle(
        (card_margin + 4, y_cursor + 4, IMAGE_WIDTH - card_margin + 4, y_cursor + cta_height + 4),
        radius=cta_height // 2,
        fill='#00000018'
    )
    # Button
    draw.rounded_rectangle(
        (card_margin, y_cursor, IMAGE_WIDTH - card_margin, y_cursor + cta_height),
        radius=cta_height // 2,
        fill=COLORS['primary']
    )

    draw.text(
        (IMAGE_WIDTH // 2, y_cursor + cta_height // 2),
        "Share your progress!",
        font=font_cta,
        fill=COLORS['text_white'],
        anchor="mm"
    )

    # ===== FOOTER =====
    draw.text(
        (IMAGE_WIDTH // 2, IMAGE_HEIGHT - 45),
        "foodierobot.com",
        font=font_footer,
        fill=COLORS['text_light'],
        anchor="mt"
    )

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG', optimize=True)
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()


def upload_progress_image(image_bytes: bytes, user_code: str) -> Optional[str]:
    """Upload progress image to Cloudinary."""
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
