import io
import os

from PIL import Image

from app.prompt_loader import (
    get_news_anchor_prompt,
    get_photo_frame_prompt,
)
from app.tools import WEB_DIR, imagen_tool, news_tool, publisher_tool


def test_prompt_loader():
    """Verify prompt loader correctly reads markdown templates and substitutes placeholders."""
    news_prompt = get_news_anchor_prompt()
    assert "News Anchor System Prompt" in news_prompt
    assert "Deduplication" in news_prompt

    # Test dynamic exclusion passing
    news_prompt_with_exclusions = get_news_anchor_prompt(
        recent_exclusions=["Headline A", "Headline B"]
    )
    assert "Recently Featured Headlines to Avoid" in news_prompt_with_exclusions
    assert "Headline A" in news_prompt_with_exclusions

    # Test morning period (08:00)
    morning_data = get_photo_frame_prompt("Test headline summary", hour=8)
    assert "Vivid Retro-Pop" in morning_data["prompt"]
    assert "90s lo-fi anime style" in morning_data["prompt"]

    # Test midday period (13:00)
    midday_data = get_photo_frame_prompt("Test headline summary", hour=13)
    assert "Electric Claymation" in midday_data["prompt"]

    # Test evening period (20:00)
    evening_data = get_photo_frame_prompt("Test headline summary", hour=20)
    assert "Luminescent Lo-Fi Digital" in evening_data["prompt"]


def test_news_tool():
    """Verify NewsTool returns 5 structured headlines with summaries."""
    result = news_tool("technology and science")
    assert result["status"] == "success"
    assert len(result["headlines"]) == 5
    assert len(result["summary"]) > 20
    assert "timestamp" in result


def test_imagen_tool_dimensions_and_styles():
    """Verify ImagenTool generates valid 1080x1920 9:16 portrait PNG images across all styles."""
    for test_hour in [8, 13, 20]:
        result = imagen_tool("1. Test Headline:\nBrief test summary.", hour=test_hour)
        assert result["status"] == "success"
        assert result["width"] == 1080
        assert result["height"] == 1920
        assert result["format"] == "PNG"

        # Verify image bytes format
        img = Image.open(io.BytesIO(result["image_bytes"]))
        assert img.size == (1080, 1920)
        assert img.mode == "RGB"


def test_publisher_tool_fifo_queue():
    """Verify PublisherTool strictly maintains 3-image FIFO queue without accumulating older files."""
    # Create 4 consecutive test images
    for i in range(1, 5):
        test_img = Image.new("RGB", (1080, 1920), color=(i * 40, i * 30, i * 20))
        buf = io.BytesIO()
        test_img.save(buf, format="PNG")

        res = publisher_tool({"image_bytes": buf.getvalue()})
        assert res["status"] == "success"
        assert os.path.exists(res["latest_image"])
        assert os.path.exists(res["index_html"])

    # Verify only image_1.png, image_2.png, image_3.png exist (image_4+ is pruned)
    assert os.path.exists(os.path.join(WEB_DIR, "image_1.png"))
    assert os.path.exists(os.path.join(WEB_DIR, "image_2.png"))
    assert os.path.exists(os.path.join(WEB_DIR, "image_3.png"))
    assert not os.path.exists(os.path.join(WEB_DIR, "image_4.png"))
    assert not os.path.exists(os.path.join(WEB_DIR, "image_5.png"))
