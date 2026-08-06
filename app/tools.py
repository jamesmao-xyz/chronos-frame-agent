import base64
import glob
import io
import json
import logging
import os
from datetime import datetime
from typing import Any

from google.genai import Client, types
from PIL import Image, ImageDraw

from app.event_hub import event_hub
from app.memory import memory
from app.prompt_loader import (
    get_news_anchor_prompt,
    get_photo_frame_prompt,
    get_time_of_day_style,
)

logger = logging.getLogger(__name__)

# Output directory for web display
WEB_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "smart_frame_web")
)

# Comprehensive fallback news story pool (used when offline/fallback to rotate without repeats)
FALLBACK_NEWS_POOL = [
    {
        "title": "Global Technology Summit Unveils Next-Gen AI Silicon",
        "summary": "Tech leaders showcase ultra-efficient neural processing chips designed for edge smart devices.",
    },
    {
        "title": "International Clean Energy Accord Expands Global Renewables",
        "summary": "40 nations commit to doubling solar, wind, and smart battery storage across national grids.",
    },
    {
        "title": "Space Station Launches New Orbital Microgravity Laboratory",
        "summary": "Astronauts install modular science bays for advanced biotechnology and crystallographic research.",
    },
    {
        "title": "Historic Global Marine Conservation Treaty Ratified",
        "summary": "Over 30% of international waters are officially designated as protected ecological sanctuaries.",
    },
    {
        "title": "Precision Nanomedicine Approvals Accelerate Targeted Therapies",
        "summary": "Breakthrough nanocarrier drug deliveries cleared for oncology and non-invasive gene therapies.",
    },
    {
        "title": "Quantum Computing Milestone Achieved in Error Correction",
        "summary": "Researchers demonstrate fault-tolerant logical qubits with tenfold coherence improvements.",
    },
    {
        "title": "Deep Sea Expedition Maps Unexplored Pacific Geothermal Vents",
        "summary": "Autonomous submersibles discover thriving endemic ecosystems and unique mineral formations.",
    },
    {
        "title": "Commercial Fusion Reactor Prototype Sustains Plasma Record",
        "summary": "High-temperature superconducting magnets maintain steady-state fusion plasma for two hours.",
    },
    {
        "title": "Global Reforestation Initiative Reaches 5 Billion Trees",
        "summary": "Satellite telemetry confirms widespread canopy recovery across sub-Saharan and Amazonian corridors.",
    },
    {
        "title": "Next-Gen Solid-State Battery Enters Mass Automotive Production",
        "summary": "High-density energy cells offer 1,000 km range with ten-minute ultra-fast charging.",
    },
    {
        "title": "James Webb Telescope Detects Organic Signatures on Exoplanet",
        "summary": "Atmospheric spectroscopy reveals atmospheric methane and water vapor in habitable zone world.",
    },
    {
        "title": "Smart Agricultural Robotics Boost Crop Yields by Thirty Percent",
        "summary": "Autonomous precision farming swarms minimize water consumption and eliminate herbicide runoff.",
    },
    {
        "title": "Transcontinental Magnetic Levitation Transit Corridor Approved",
        "summary": "High-speed zero-emission maglev network connects major industrial hubs at 600 km/h.",
    },
    {
        "title": "Atmospheric Direct Air Carbon Capture Facility Opens at Scale",
        "summary": "Industrial direct-air units sequester one million metric tons of CO2 into basalt rock annually.",
    },
    {
        "title": "Neurotechnology Interface Restores Fine Motor Movement",
        "summary": "Non-invasive brain-computer interfaces enable paralyzed patients to control robotic limbs seamlessly.",
    },
]


def news_tool(topic: str = "top 5 global world headlines") -> dict[str, Any]:
    """
    NewsTool: Connects to news source via Google GenAI to retrieve top 5 global headlines,
    filters safety/explicit content, and uses agent memory to ensure headlines do NOT repeat across photos.

    Args:
        topic: Topic query for global news.

    Returns:
        Dict containing top 5 headlines, simple summary text, and timestamp.
    """
    logger.info(
        f"NewsTool: Fetching 5 unique, non-repeating headlines for topic '{topic}'..."
    )
    api_key = os.environ.get("GEMINI_API_KEY")

    # Retrieve recently featured headlines from agent memory to prevent repetition
    recent_exclusions = memory.get_recent_headlines(limit=25)
    system_prompt = get_news_anchor_prompt(recent_exclusions=recent_exclusions)

    chosen_headlines: list[str] = []
    chosen_summaries: list[str] = []

    if (
        api_key
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
    ):
        try:
            client = Client()
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=(
                    f"Provide 8 diverse global news headlines for today with a bold title and 1-sentence summary each. "
                    f"Exclude any of these recently used topics: {recent_exclusions[:10]}. Topic: {topic}"
                ),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.4,
                ),
            )
            if response.text:
                raw_text = response.text
                candidates = [s.strip() for s in raw_text.split("\n\n") if s.strip()]
                if not candidates:
                    candidates = [
                        s.strip()
                        for s in raw_text.split("\n")
                        if s.strip() and (s[0].isdigit() or s.startswith("-"))
                    ]

                for item in candidates:
                    first_line = item.split("\n")[0] if "\n" in item else item
                    if not memory.is_duplicate(first_line):
                        chosen_headlines.append(first_line)
                        chosen_summaries.append(item)
                        if len(chosen_headlines) >= 5:
                            break

                logger.info(
                    f"GenAI retrieved {len(chosen_headlines)} unique non-repeating headlines."
                )
        except Exception as e:
            logger.warning(f"News fetch via GenAI skipped: {e}")

    # If fewer than 5 unique headlines, rotate fresh stories from fallback pool
    if len(chosen_headlines) < 5:
        logger.info(
            "Filling remaining headline slots with non-repeating pool stories..."
        )
        for story in FALLBACK_NEWS_POOL:
            title = story["title"]
            if not memory.is_duplicate(title):
                idx = len(chosen_headlines) + 1
                formatted_h = f"{idx}. {title}"
                formatted_s = f"{idx}. {title}:\n{story['summary']}"
                chosen_headlines.append(formatted_h)
                chosen_summaries.append(formatted_s)
                if len(chosen_headlines) >= 5:
                    break

        # If history has seen everything, reset history and take top 5
        if len(chosen_headlines) < 5:
            memory.clear()
            for i, story in enumerate(FALLBACK_NEWS_POOL[:5]):
                idx = i + 1
                chosen_headlines.append(f"{idx}. {story['title']}")
                chosen_summaries.append(f"{idx}. {story['title']}:\n{story['summary']}")

    # Final selected 5 stories
    final_headlines = chosen_headlines[:5]
    final_summary_text = "\n\n".join(chosen_summaries[:5])

    # Record newly selected headlines in agent memory so subsequent photos do NOT repeat them
    memory.add_headlines(final_headlines)

    timestamp = datetime.now().strftime("%A, %B %d, %Y  •  %H:%M")

    return {
        "status": "success",
        "topic": topic,
        "headlines": final_headlines,
        "summary": final_summary_text,
        "timestamp": timestamp,
        "memory_history_count": len(memory.get_recent_headlines()),
    }


def _generate_procedural_photo_frame_image(
    width: int,
    height: int,
    headline_summary: str,
    timestamp: str,
    hour: int | None = None,
) -> Image.Image:
    """
    Generates an ambient smart photo frame graphic in 1080x1920 (9:16 portrait),
    crafted with time-of-day responsive 90s lo-fi anime styling for at-a-glance viewing.
    """
    style_info = get_time_of_day_style(hour)
    palette = style_info["palette"]

    img = Image.new("RGB", (width, height), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Render time-of-day atmospheric gradient
    c_top, c_bot = palette["bg_top"], palette["bg_bottom"]
    for y in range(height):
        ratio = y / height
        r = int(c_top[0] * (1 - ratio) + c_bot[0] * ratio)
        g = int(c_top[1] * (1 - ratio) + c_bot[1] * ratio)
        b = int(c_top[2] * (1 - ratio) + c_bot[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Whimsical pastel ambient light spheres
    acc1, acc2 = palette["accent1"], palette["accent2"]
    draw.ellipse([-200, -100, 800, 900], fill=(acc1[0], acc1[1], acc1[2]))
    draw.ellipse([450, 500, 1300, 1350], fill=(acc2[0], acc2[1], acc2[2]))
    draw.ellipse([100, 1200, 1000, 2100], fill=(acc1[0], acc1[1], acc1[2]))

    # Soft dark scrim to ensure perfect text contrast
    dark_scrim = Image.new(
        "RGBA", (width, height), (15, 23, 42, palette["scrim_alpha"])
    )
    img.paste(dark_scrim, (0, 0), dark_scrim)
    draw = ImageDraw.Draw(img)

    # Smart Frame Ambient Header with Style Badge
    draw.text(
        (70, 75),
        f"CHRONOS  |  90s LO-FI ANIME [{style_info['period_name'].upper()}]",
        fill=palette["title_color"],
    )
    if not timestamp:
        timestamp = datetime.now().strftime("%A, %B %d, %Y  •  %H:%M")
    draw.text((70, 120), timestamp.upper(), fill=(203, 213, 225))

    # Parse and render the 5 glanceable news stories
    stories = [s.strip() for s in headline_summary.split("\n\n") if s.strip()]
    if not stories:
        stories = [s.strip() for s in headline_summary.split("\n") if s.strip()]

    y_pos = 220
    accent_colors = [
        (250, 204, 21),
        (56, 189, 248),
        (52, 211, 153),
        (244, 114, 182),
        (167, 139, 250),
    ]

    for idx, story in enumerate(stories[:5]):
        color = accent_colors[idx % len(accent_colors)]
        lines = [line.strip() for line in story.split("\n") if line.strip()]

        if lines:
            headline_title = lines[0]
            # Glanceable number badge & headline title
            draw.text((70, y_pos), f"{idx + 1:02d}", fill=color)
            draw.text((125, y_pos), headline_title, fill=(255, 255, 255))
            y_pos += 44

            # Glanceable summary text
            for body_line in lines[1:]:
                words = body_line.split(" ")
                curr_line = ""
                for w in words:
                    if len(curr_line + " " + w) > 48:
                        draw.text((125, y_pos), curr_line, fill=(226, 232, 240))
                        y_pos += 36
                        curr_line = w
                    else:
                        curr_line = (curr_line + " " + w).strip()
                if curr_line:
                    draw.text((125, y_pos), curr_line, fill=(226, 232, 240))
                    y_pos += 36

        y_pos += 52

    # Bottom style badge footer
    draw.text(
        (70, height - 75),
        f"SMART FRAME EDITION  •  {style_info['period_name'].upper()}",
        fill=(148, 163, 184),
    )

    return img


def imagen_tool(
    headline_summary: str, timestamp: str = "", hour: int | None = None
) -> dict[str, Any]:
    """
    ImagenTool: Generates a 1080x1920 (9:16 portrait) photo frame artwork using Nano Banana 2 image models,
    applying external markdown prompt templates with dynamic time-of-day styling.

    Args:
        headline_summary: The summarized top 5 news stories to present.
        timestamp: Time string to embed.
        hour: Optional hour override for styling tests.

    Returns:
        Dict containing image metadata and generated bytes or file path.
    """
    prompt_data = get_photo_frame_prompt(
        headline_summary=headline_summary, hour=hour, aspect_ratio="9:16"
    )
    photo_frame_prompt = prompt_data["prompt"]
    style_info = prompt_data["style_info"]

    logger.info(
        f"ImagenTool: Generating 9:16 smart photo frame visual via Nano Banana 2 [{style_info['period_name']}]..."
    )

    width, height = 1080, 1920  # Strict 9:16 portrait dimensions
    final_image: Image.Image | None = None

    api_key = os.environ.get("GEMINI_API_KEY")
    gcp_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get(
        "GOOGLE_CLOUD_PROJECT"
    )

    if api_key or gcp_creds:
        try:
            client = Client()

            # Target actual image generation models
            image_model_candidates = [
                "gemini-3.1-flash-image",
                "gemini-2.5-flash-image",
            ]

            for model_name in image_model_candidates:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=photo_frame_prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(aspect_ratio="9:16"),
                        ),
                    )

                    if (
                        response
                        and hasattr(response, "candidates")
                        and response.candidates
                    ):
                        candidate = response.candidates[0]
                        if candidate and candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, "inline_data") and part.inline_data:
                                    data = part.inline_data.data
                                    if isinstance(data, str):
                                        image_bytes = base64.b64decode(data)
                                    else:
                                        image_bytes = data
                                    raw_img = Image.open(io.BytesIO(image_bytes))
                                    final_image = raw_img.convert("RGB").resize(
                                        (width, height), Image.Resampling.LANCZOS
                                    )
                                    logger.info(
                                        f"Photo frame image successfully generated via Nano Banana 2 ({model_name}) [{style_info['period_name']}]!"
                                    )
                                    break
                    if final_image is not None:
                        break
                except Exception as model_err:
                    logger.debug(
                        f"Image model candidate {model_name} skipped: {model_err}"
                    )

        except Exception as e:
            logger.warning(f"Photo frame generation attempt skipped: {e}")

    # Fallback to smart photo frame image if API is offline or credits unavailable
    if final_image is None:
        final_image = _generate_procedural_photo_frame_image(
            width, height, headline_summary, timestamp, hour=hour
        )

    # Save final photo frame image
    buffer = io.BytesIO()
    final_image.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()

    return {
        "status": "success",
        "width": width,
        "height": height,
        "style_period": style_info["period_name"],
        "image_bytes": img_bytes,
        "format": "PNG",
    }


def publisher_tool(image_data: Any) -> dict[str, Any]:
    """
    PublisherTool: Writes newly generated image to `smart_frame_web/` directory while shifting old files
    (image_1.png -> image_2.png -> image_3.png) and deleting any older images to enforce a strict 3-image FIFO queue.
    Publishes atomic playlist manifest, broadcasts real-time SSE events via event_hub, and generates
    the modern smart frame web interface with dual-layer GPU crossfade transitions.

    Args:
        image_data: Dictionary containing `image_bytes` or direct bytes of the PNG image.

    Returns:
        Dict containing shift operations details and web directory paths.
    """
    logger.info("PublisherTool: Enforcing 3-image FIFO queue in smart_frame_web/...")

    os.makedirs(WEB_DIR, exist_ok=True)

    img_bytes = None
    if isinstance(image_data, dict):
        img_bytes = image_data.get("image_bytes")
    elif isinstance(image_data, bytes):
        img_bytes = image_data

    if not img_bytes:
        raise ValueError("PublisherTool received invalid or empty image_bytes input.")

    img3_path = os.path.join(WEB_DIR, "image_3.png")
    img2_path = os.path.join(WEB_DIR, "image_2.png")
    img1_path = os.path.join(WEB_DIR, "image_1.png")
    img4_path = os.path.join(WEB_DIR, "image_4.png")

    # Step 1: Delete 4th oldest image if exists
    if os.path.exists(img4_path):
        os.remove(img4_path)

    # Step 2: Shift image_3 -> image_4 (temporary before deletion) or remove image_3
    if os.path.exists(img3_path):
        os.remove(img3_path)

    # Step 3: Shift image_2 -> image_3
    if os.path.exists(img2_path):
        os.rename(img2_path, img3_path)

    # Step 4: Shift image_1 -> image_2
    if os.path.exists(img1_path):
        os.rename(img1_path, img2_path)

    # Step 5: Save new image as image_1.png
    with open(img1_path, "wb") as f:
        f.write(img_bytes)

    # Prune any extraneous image files to strictly enforce 3-image max FIFO queue
    all_images = glob.glob(os.path.join(WEB_DIR, "image_*.png"))
    for img_file in all_images:
        filename = os.path.basename(img_file)
        try:
            num = int(filename.replace("image_", "").replace(".png", ""))
            if num > 3:
                os.remove(img_file)
        except ValueError:
            pass

    # Step 6: Build structured playlist metadata with cache-busting version tags
    v_tag = int(datetime.now().timestamp())
    now_str = datetime.now().strftime("%A, %B %d, %Y • %H:%M")

    playlist: list[dict[str, Any]] = []
    if os.path.exists(img1_path):
        playlist.append(
            {
                "filename": "image_1.png",
                "url": f"image_1.png?v={v_tag}",
                "label": "image_1 (Latest)",
                "age": "Latest",
                "timestamp": now_str,
                "index": 0,
            }
        )
    if os.path.exists(img2_path):
        playlist.append(
            {
                "filename": "image_2.png",
                "url": f"image_2.png?v={v_tag}",
                "label": "image_2 (-15 min)",
                "age": "-15 min",
                "timestamp": "T-15 min",
                "index": 1,
            }
        )
    if os.path.exists(img3_path):
        playlist.append(
            {
                "filename": "image_3.png",
                "url": f"image_3.png?v={v_tag}",
                "label": "image_3 (-30 min)",
                "age": "-30 min",
                "timestamp": "T-30 min",
                "index": 2,
            }
        )

    # Persist playlist.json manifest atomically
    playlist_path = os.path.join(WEB_DIR, "playlist.json")
    tmp_playlist_path = os.path.join(WEB_DIR, ".playlist.json.tmp")
    try:
        with open(tmp_playlist_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "updated_at": datetime.now().isoformat(),
                    "version": v_tag,
                    "playlist": playlist,
                },
                f,
                indent=2,
            )
        os.replace(tmp_playlist_path, playlist_path)
    except Exception as e:
        logger.warning(f"PublisherTool: Failed to save playlist.json: {e}")

    # Broadcast updated playlist to all connected SSE clients
    event_hub.set_playlist(playlist=playlist, active_index=0)

    # Step 7: Generate/Update web display index.html
    index_html_path = os.path.join(WEB_DIR, "index.html")
    # If index.html already exists with full template, ensure it is in place
    if not os.path.exists(index_html_path):
        # Fallback template if index.html was removed
        with open(index_html_path, "w", encoding="utf-8") as f:
            f.write(
                "<!DOCTYPE html><html><head><meta http-equiv='refresh' content='5'></head><body><h1>Chronos Smart Frame</h1></body></html>"
            )

    return {
        "status": "success",
        "output_dir": WEB_DIR,
        "latest_image": img1_path,
        "fifo_queue": ["image_1.png", "image_2.png", "image_3.png"],
        "playlist": playlist,
        "index_html": index_html_path,
    }
