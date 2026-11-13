import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_render_input import build_render_input


class FakeD1:
    def __init__(self, item):
        self.item = item

    def get_content_item_for_render(self, content_id, profile_id):
        return self.item


def item():
    return {
        "title": "Test draft",
        "script_data": {
            "voiceover_text": "A short educational narration.",
            "visual_direction": "Clean motion graphics",
            "duration_seconds": 25,
        },
    }


class BuildRenderInputTests(unittest.TestCase):
    def test_tiktok_render_input_requires_music(self):
        result = build_render_input(FakeD1(item()), "content-1", "tiktok_pieknemedia")
        self.assertEqual("humor", result["theme"])
        self.assertEqual("tiktok", result["platform"])
        self.assertTrue(result["music_required"])
        self.assertTrue(result["cta"])

    def test_youtube_render_input_uses_tech_theme_without_forced_music(self):
        result = build_render_input(FakeD1(item()), "content-2", "youtube_memoryagent")
        self.assertEqual("tech", result["theme"])
        self.assertEqual("youtube", result["platform"])
        self.assertFalse(result["music_required"])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported_render_profile"):
            build_render_input(FakeD1(item()), "content-3", "unknown_profile")


if __name__ == "__main__":
    unittest.main()
