import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# Root directory of prompt markdown files
PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))


def get_current_local_time() -> datetime:
    """Returns the current datetime in the configured local timezone (defaults to Australia/Sydney)."""
    tz_name = os.environ.get("TZ", "Australia/Sydney")
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()


def _read_prompt_file(filename: str) -> str:
    """Reads content from a markdown prompt file."""
    filepath = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Prompt file not found at: {filepath}")
    with open(filepath, encoding="utf-8") as f:
        return f.read().strip()


def get_news_anchor_prompt(recent_exclusions: list[str] | None = None) -> str:
    """Returns the system prompt for NewsTool with dynamic memory exclusion list."""
    base_prompt = _read_prompt_file("news_anchor.md")
    if recent_exclusions:
        exclusions_block = (
            "\n\n## Recently Featured Headlines to Avoid (DO NOT REPEAT):\n"
            + "\n".join(f"- {title}" for title in recent_exclusions[:25])
        )
        return base_prompt + exclusions_block
    return base_prompt


def get_time_of_day_style(hour: int | None = None) -> dict[str, Any]:
    """
    Computes time-of-day specific visual style modifier and palette for Nano Banana 3D figure aesthetic:
    - 00:00 - 10:00 (Morning): 'Sunrise Vinyl Pop'
    - 10:00 - 16:00 (Daytime): 'Electric Matte Figurine'
    - 16:00 - 24:00 (Evening/Night): 'Luminescent Cyber-Toy'
    """
    if hour is None:
        hour = get_current_local_time().hour

    if 0 <= hour < 10:
        period_name = "Sunrise Vinyl Pop (Morning)"
        style_doc = _read_prompt_file("styles/morning_retro_pop.md")
        modifier = (
            "Sunrise Vinyl Pop aesthetic, Nano Banana iconic 3D figure style, vibrant morning sunrise studio key lighting, "
            "glossy pastel vinyl toy textures, charming stylized 3D collectible figurines in a miniature diorama"
        )
        palette = {
            "bg_top": (253, 224, 71),  # Bright morning pastel yellow
            "bg_bottom": (244, 114, 182),  # Warm retro candy pink
            "accent1": (56, 189, 248),  # Pop cyan
            "accent2": (234, 88, 12),  # Vivid orange
            "scrim_alpha": 180,
            "title_color": (254, 240, 138),
        }
    elif 10 <= hour < 16:
        period_name = "Electric Matte Figurine (Midday)"
        style_doc = _read_prompt_file("styles/midday_claymation.md")
        modifier = (
            "Electric Matte Figurine aesthetic, Nano Banana iconic 3D figure style, high-clarity daylight studio three-point lighting, "
            "smooth sculpted matte resin figurines, tactile colorful 3D designer toy diorama with gentle ambient occlusion"
        )
        palette = {
            "bg_top": (249, 115, 22),  # Electric figurine orange
            "bg_bottom": (99, 102, 241),  # Electric indigo
            "accent1": (52, 211, 153),  # Mint resin
            "accent2": (236, 72, 153),  # Hot magenta figurine
            "scrim_alpha": 185,
            "title_color": (253, 230, 138),
        }
    else:  # 16:00 - 24:00
        period_name = "Luminescent Cyber-Toy (Evening)"
        style_doc = _read_prompt_file("styles/evening_luminescent.md")
        modifier = (
            "Luminescent Cyber-Toy aesthetic, Nano Banana iconic 3D figure style, glowing neon twilight ambient bloom, "
            "translucent luminescent vinyl 3D collectible figures, dreamy cozy nighttime diorama lighting"
        )
        palette = {
            "bg_top": (30, 27, 75),  # Deep nighttime indigo
            "bg_bottom": (15, 23, 42),  # Midnight slate
            "accent1": (168, 85, 247),  # Luminescent purple
            "accent2": (56, 189, 248),  # Glowing cyan
            "scrim_alpha": 195,
            "title_color": (192, 132, 252),
        }

    return {
        "period_name": period_name,
        "modifier": modifier,
        "style_doc": style_doc,
        "palette": palette,
    }


def get_photo_frame_prompt(
    headline_summary: str, hour: int | None = None, aspect_ratio: str = "9:16"
) -> dict[str, Any]:
    """
    Constructs the full photo frame image generation prompt by loading markdown templates.
    """
    style_info = get_time_of_day_style(hour)
    template = _read_prompt_file("photo_frame_image.md")

    # Format the prompt with full headline summary
    formatted_prompt = template.format(
        aspect_ratio=aspect_ratio,
        time_of_day_style=style_info["modifier"],
        headline_summary=headline_summary[:1500],
    )

    return {"prompt": formatted_prompt, "style_info": style_info}
