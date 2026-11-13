import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from autored.media_validation import MediaValidationError, validate_tiktok_video


class MediaValidationTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("fake-video.mp4")
        self.path.write_bytes(b"video-bytes")
        self.addCleanup(lambda: self.path.unlink(missing_ok=True))
        self.probe = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
            "format": {"duration": "24.0"},
        }

    def runner(self, probe):
        def run(*args, **kwargs):
            return SimpleNamespace(stdout=json.dumps(probe))
        return run

    def test_valid_vertical_h264_aac_video_passes(self):
        result = validate_tiktok_video(self.path, self.runner(self.probe))
        self.assertEqual(1080, result["width"])
        self.assertEqual(1920, result["height"])
        self.assertEqual(24.0, result["duration_seconds"])

    def test_landscape_video_is_blocked(self):
        invalid = json.loads(json.dumps(self.probe))
        invalid["streams"][0]["width"] = 1920
        invalid["streams"][0]["height"] = 1080
        with self.assertRaisesRegex(MediaValidationError, "vertical_aspect_ratio_required"):
            validate_tiktok_video(self.path, self.runner(invalid))

    def test_missing_audio_stream_is_blocked(self):
        invalid = {"streams": [self.probe["streams"][0]], "format": {"duration": "24"}}
        with self.assertRaisesRegex(MediaValidationError, "audio_stream_missing"):
            validate_tiktok_video(self.path, self.runner(invalid))

    def test_wrong_audio_specification_is_blocked(self):
        invalid = json.loads(json.dumps(self.probe))
        invalid["streams"][1]["sample_rate"] = "44100"
        with self.assertRaisesRegex(MediaValidationError, "aac_48khz_stereo_required"):
            validate_tiktok_video(self.path, self.runner(invalid))

    def test_duration_outside_range_is_blocked(self):
        invalid = json.loads(json.dumps(self.probe))
        invalid["format"]["duration"] = "120"
        with self.assertRaisesRegex(MediaValidationError, "duration_out_of_tiktok_range"):
            validate_tiktok_video(self.path, self.runner(invalid))


if __name__ == "__main__":
    unittest.main()
