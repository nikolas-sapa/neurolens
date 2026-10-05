from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_unexpected_analysis_failure_does_not_expose_exception(caplog):
    marker = "fixture-private-file-marker"
    with patch("app.main.route_content", side_effect=RuntimeError(marker)):
        response = TestClient(app).post("/analyze", data={"text_content": "fixture"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Analysis failed. Check server logs for details."
    assert marker not in response.text
    assert marker in caplog.text


def test_invalid_video_url_rejected_before_downloader():
    with patch("app.processors.youtube_processor.yt_dlp.YoutubeDL") as downloader:
        with TestClient(app) as client:
            response = client.post("/analyze", data={"youtube_url": "https://127.0.0.1/private"})
            comparison = client.post("/compare", data={"youtube_url_a": "https://youtube.com/redirect?q=private", "text_b": "fixture"})
    assert response.status_code == 422
    assert comparison.status_code == 422
    downloader.assert_not_called()
