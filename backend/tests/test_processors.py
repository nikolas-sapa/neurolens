import pytest
from PIL import Image
import numpy as np
import unittest.mock as mock
from app.brain_mapper import REGIONS


def _make_png(path: str):
    img = Image.fromarray(np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8))
    img.save(path)
    return path


@pytest.mark.model_integration
def test_process_image_has_all_region_keys(tmp_path):
    from app.processors.image_processor import process_image
    p = _make_png(str(tmp_path / "t.png"))
    out = process_image(p)
    assert out["type"] == "image"
    assert set(out["scores"].keys()) == set(REGIONS.keys())
    assert all(0 <= v <= 100 for v in out["scores"].values())


def test_chunk_text_splits_long_input():
    from app.processors.text_processor import chunk_text
    long = " ".join(["word"] * 500)
    chunks = chunk_text(long)
    assert len(chunks) > 1


def test_chunk_text_keeps_short_input_as_one():
    from app.processors.text_processor import chunk_text
    assert len(chunk_text("Buy now, limited time only!")) == 1


@pytest.mark.model_integration
def test_process_text_has_scores():
    from app.processors.text_processor import process_text
    out = process_text("This product will transform your life.")
    assert out["type"] == "text"
    assert all(0 <= v <= 100 for v in out["scores"].values())


@pytest.mark.model_integration
def test_process_pdf_extracts_and_scores(tmp_path):
    from app.processors.pdf_processor import process_pdf
    mock_page = mock.MagicMock()
    mock_page.extract_text.return_value = "Amazing product, buy now, transform your life today!"
    mock_pdf = mock.MagicMock()
    mock_pdf.__enter__ = mock.MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = mock.MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]
    with mock.patch("pdfplumber.open", return_value=mock_pdf):
        out = process_pdf("/fake/path.pdf")
    assert out["type"] == "pdf"
    assert out["meta"]["page_count"] == 1
    assert all(0 <= v <= 100 for v in out["scores"].values())


def test_extract_frames_produces_pil_images():
    from app.processors.video_processor import extract_frames
    cap = mock.MagicMock()
    cap.isOpened.side_effect = [True, True, False]
    cap.get.return_value = 25.0
    cap.read.side_effect = [
        (True, np.zeros((480, 640, 3), dtype=np.uint8)),
        (False, None),
    ]
    with mock.patch("cv2.VideoCapture", return_value=cap):
        frames = extract_frames("/fake/vid.mp4", fps=1)
    assert len(frames) >= 1
    from PIL import Image as PILImage
    assert all(isinstance(f, PILImage.Image) for f in frames)


@pytest.mark.model_integration
def test_process_video_merges_visual_and_audio():
    from app.processors.video_processor import process_video
    with mock.patch("app.processors.video_processor.extract_frames") as ef, \
         mock.patch("app.processors.video_processor.transcribe_audio") as ta:
        ef.return_value = [Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))]
        ta.return_value = "Amazing product buy now limited offer"
        out = process_video("/fake/vid.mp4")
    assert out["type"] == "video"
    assert all(0 <= v <= 100 for v in out["scores"].values())


_MOCK_SCORES = {k: 50 for k in ["visual_cortex", "amygdala", "face_social", "hippocampus", "language_areas", "reward_circuit", "prefrontal", "motor_action"]}


def test_process_youtube_delegates_to_video(tmp_path):
    from app.processors.youtube_processor import process_youtube
    with mock.patch("app.processors.youtube_processor.download_youtube") as dl, \
         mock.patch("app.processors.youtube_processor.process_video") as pv:
        dl.return_value = {"video_path": "/tmp/abc.mp4", "title": "Test Ad", "player_client": "ios"}
        pv.return_value = {"type": "video", "scores": _MOCK_SCORES, "meta": {}}
        out = process_youtube("https://youtube.com/watch?v=x", tmp_dir=str(tmp_path))
    assert out["type"] == "youtube"
    assert out["meta"]["title"] == "Test Ad"
    assert out["meta"]["player_client"] == "ios"
    dl.assert_called_once()
    pv.assert_called_once()


def test_download_youtube_falls_back_through_clients(tmp_path):
    """First two clients fail with the same SSL error YouTube returns from cloud
    IPs; the third succeeds. download_youtube should cycle through them."""
    from app.processors.youtube_processor import download_youtube
    fake_info = {"id": "abc", "ext": "mp4", "title": "Video"}

    class FakeYDL:
        instances = 0

        def __init__(self, opts):
            FakeYDL.instances += 1
            self.client = opts["extractor_args"]["youtube"]["player_client"][0]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def extract_info(self, url, download):
            if FakeYDL.instances <= 2:
                raise RuntimeError(f"SSL UNEXPECTED_EOF (client={self.client})")
            return fake_info

        def prepare_filename(self, info):
            return os.path.join(str(tmp_path), "abc.mp4")

    import os
    with mock.patch("app.processors.youtube_processor.yt_dlp.YoutubeDL", FakeYDL):
        result = download_youtube("https://youtube.com/watch?v=abcdefghijk", str(tmp_path))
    assert result["title"] == "Video"
    assert FakeYDL.instances == 3  # cycled through ios + android, succeeded on web_safari


def test_download_youtube_raises_blocked_when_all_clients_fail(tmp_path):
    from app.processors.youtube_processor import download_youtube, YouTubeBlockedError

    class AlwaysFails:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def extract_info(self, url, download):
            raise RuntimeError("SSL UNEXPECTED_EOF")

    with mock.patch("app.processors.youtube_processor.yt_dlp.YoutubeDL", AlwaysFails):
        with pytest.raises(YouTubeBlockedError, match="blocked every download"):
            download_youtube("https://youtube.com/watch?v=abcdefghijk", str(tmp_path))


def test_process_video_uses_clip_scores(tmp_path):
    from unittest.mock import patch, MagicMock
    from app.processors.video_processor import process_video

    fake_video = tmp_path / "ad.mp4"
    fake_video.write_bytes(b"fake")
    all_regions = [
        "visual_cortex", "amygdala", "face_social", "hippocampus",
        "language_areas", "reward_circuit", "prefrontal", "motor_action",
    ]
    clip_scores = {k: 55 for k in all_regions}

    with patch("app.processors.video_processor.extract_frames", return_value=[MagicMock()]), \
         patch("app.processors.video_processor.transcribe_audio", return_value="hello"), \
         patch("app.brain_mapper.get_brain_scores", return_value=clip_scores):
        result = process_video(str(fake_video))

    for region, score in result["scores"].items():
        assert score == 55, f"{region} should be 55, got {score}"
    assert result["meta"]["frame_count"] == 1
    assert result["meta"]["transcript_preview"] == "hello"


def test_process_video_no_frames_or_transcript_returns_zeros(tmp_path):
    from unittest.mock import patch
    from app.processors.video_processor import process_video

    fake_video = tmp_path / "ad.mp4"
    fake_video.write_bytes(b"fake")

    with patch("app.processors.video_processor.extract_frames", return_value=[]), \
         patch("app.processors.video_processor.transcribe_audio", return_value=""):
        result = process_video(str(fake_video))

    assert all(v == 0 for v in result["scores"].values())
