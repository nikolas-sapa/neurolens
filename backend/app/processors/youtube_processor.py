import logging
import os
import re
from urllib.parse import parse_qs, urlsplit
import yt_dlp

from app.processors.video_processor import process_video

_log = logging.getLogger(__name__)

# YouTube aggressively blocks the default 'web' player from cloud IPs (AWS,
# HF Spaces, GCP). Falling back through alternate player clients usually works
# for at least one of them at any given time.
_PLAYER_CLIENTS = ["ios", "android", "web_safari", "web"]


class YouTubeBlockedError(RuntimeError):
    """Raised when every player-client fallback failed to download."""


class InvalidVideoURLError(ValueError):
    """A URL outside the supported single-video platforms."""


def validate_video_url(url: str) -> None:
    error = "Provide a supported video URL from YouTube, TikTok, or Instagram."
    if not isinstance(url, str) or any(ord(c) <= 32 for c in url):
        raise InvalidVideoURLError(error)
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
            raise InvalidVideoURLError(error)
        host = parsed.hostname
        path = parsed.path
        valid = False
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            ids = parse_qs(parsed.query).get("v", [])
            valid = (path == "/watch" and len(ids) == 1 and re.fullmatch(r"[A-Za-z0-9_-]{11}", ids[0])) or re.fullmatch(r"/(?:shorts|embed|live)/[A-Za-z0-9_-]{11}/?", path)
        elif host == "youtu.be":
            valid = re.fullmatch(r"/[A-Za-z0-9_-]{11}/?", path)
        elif host in {"tiktok.com", "www.tiktok.com", "m.tiktok.com"}:
            valid = re.fullmatch(r"/@[A-Za-z0-9_.]+/video/[0-9]+/?", path)
        elif host in {"instagram.com", "www.instagram.com"}:
            valid = re.fullmatch(r"/(?:p|reel|tv)/[A-Za-z0-9_-]+/?", path)
        if not valid:
            raise InvalidVideoURLError(error)
    except ValueError as exc:
        raise InvalidVideoURLError(error) from exc


def _opts_for(client: str, tmp_dir: str) -> dict:
    return {
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": [client]}},
        "socket_timeout": 30,
        "noplaylist": True,
        "allowed_extractors": ["youtube$", "tiktok$", "instagram$"],
    }


def download_youtube(url: str, tmp_dir: str) -> dict:
    validate_video_url(url)
    last_err: Exception | None = None
    for client in _PLAYER_CLIENTS:
        try:
            with yt_dlp.YoutubeDL(_opts_for(client, tmp_dir)) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                video_path = os.path.splitext(filename)[0] + ".mp4"
                return {
                    "video_path": video_path,
                    "title": info.get("title", "Unknown"),
                    "player_client": client,
                }
        except Exception as exc:
            _log.warning("yt-dlp %s client failed for %s: %s", client, url, exc)
            last_err = exc

    raise YouTubeBlockedError(
        "YouTube blocked every download attempt from this server's IP. "
        "This is common on free cloud hosts (HF Spaces, AWS, GCP). "
        "Workarounds: (1) download the video locally and upload the .mp4 file, "
        "or (2) run NeuroPulse on your own machine. "
    ) from last_err


def process_youtube(url: str, tmp_dir: str = "/tmp") -> dict:
    downloaded = download_youtube(url, tmp_dir)
    out = process_video(downloaded["video_path"])
    out["type"] = "youtube"
    out["meta"]["title"] = downloaded["title"]
    out["meta"]["url"] = url
    out["meta"]["player_client"] = downloaded.get("player_client")
    return out
