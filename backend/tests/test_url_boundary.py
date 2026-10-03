from unittest.mock import patch

import pytest

from app.processors.youtube_processor import download_youtube


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/private", "https://localhost/private",
    "https://youtube.com.evil.invalid/watch?v=abcdefghijk",
    "https://evil.invalid/video", "https://user:pass@youtube.com/watch?v=abcdefghijk",
    "https://youtube.com:8443/watch?v=abcdefghijk",
    "https://@youtube.com/watch?v=abcdefghijk", "https://:@youtube.com/watch?v=abcdefghijk",
    "https://youtube.com/redirect?q=https://127.0.0.1",
    "https://youtube.com/playlist?list=private",
    "file:///etc/passwd", "https://instagram.com/redirect/",
    "https://tiktok.com/@user", "https://youtube.com/watch?v=abcdefghijk&v=lmnopqrstuv",
])
def test_rejects_unsupported_urls_before_downloader(url, tmp_path):
    with patch("app.processors.youtube_processor.yt_dlp.YoutubeDL") as downloader:
        downloader.return_value.__enter__.return_value.extract_info.return_value = {"title": "fixture"}
        downloader.return_value.__enter__.return_value.prepare_filename.return_value = str(tmp_path / "fixture.mp4")
        with pytest.raises(ValueError, match="supported video URL"):
            download_youtube(url, str(tmp_path))
        downloader.assert_not_called()


@pytest.mark.parametrize("url", [
    "https://youtube.com/watch?v=abcdefghijk",
    "https://youtu.be/abcdefghijk", "https://www.youtube.com/shorts/abcdefghijk",
    "https://www.tiktok.com/@creator/video/1234567890123456789",
    "https://www.instagram.com/reel/abcdefghijk/",
])
def test_supported_video_urls_preserve_download(url, tmp_path):
    with patch("app.processors.youtube_processor.yt_dlp.YoutubeDL") as downloader:
        instance = downloader.return_value.__enter__.return_value
        instance.extract_info.return_value = {"title": "fixture"}
        instance.prepare_filename.return_value = str(tmp_path / "fixture.mp4")
        result = download_youtube(url, str(tmp_path))
        assert result["title"] == "fixture"
        instance.extract_info.assert_called_once_with(url, download=True)
        assert downloader.call_args.args[0]["noplaylist"] is True
        assert "generic" not in downloader.call_args.args[0]["allowed_extractors"]
