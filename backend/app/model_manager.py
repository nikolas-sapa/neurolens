"""Thin shim around the CLIP scorer that preserves the public surface
(`get_manager()`, `LowMemoryError`, `idle watchdog`, `unload`) used by the
rest of the app and the existing `/model/*` endpoints. Implementation now
delegates to `clip_scorer.CLIPScorer`."""
from __future__ import annotations

import gc
import logging
import threading
import time

from app import clip_scorer
from app.clip_scorer import CLIP_MODEL_ID, get_scorer

_log = logging.getLogger(__name__)

MODEL_ID = CLIP_MODEL_ID


class LowMemoryError(RuntimeError):
    """Kept for backwards compatibility with existing exception handlers."""


class ModelManager:
    def __init__(self, idle_timeout: int = 600):
        self._lock = clip_scorer._lifecycle_lock
        self._idle_timeout = idle_timeout
        self._watchdog = threading.Thread(target=self._idle_watchdog, daemon=True)
        self._watchdog.start()

    @property
    def _last_used(self) -> float:
        return clip_scorer._last_used

    @_last_used.setter
    def _last_used(self, value: float) -> None:
        clip_scorer._last_used = value

    @property
    def loaded(self) -> bool:
        return get_scorer().loaded

    def get(self) -> tuple[object, object]:
        """Backwards compat — returns (scorer, scorer) so old call sites that
        unpacked (model, processor) still work without crashing. New code should
        call get_scorer() directly."""
        with self._lock:
            scorer = get_scorer()
            scorer.load()
            self._last_used = time.monotonic()
            return scorer, scorer

    def unload(self) -> bool:
        with self._lock:
            did = get_scorer().unload()
            gc.collect()
            return did

    def status(self) -> dict:
        with self._lock:
            last_used = self._last_used
            idle_for = time.monotonic() - last_used if last_used else None
            return {
                "loaded": self.loaded,
                "model_id": MODEL_ID,
                "idle_timeout_seconds": self._idle_timeout,
                "idle_for_seconds": round(idle_for, 1) if idle_for is not None else None,
            }

    def _unload_if_idle(self) -> bool:
        with self._lock:
            last_used = self._last_used
            if not last_used or not self.loaded:
                return False
            if time.monotonic() - last_used <= self._idle_timeout:
                return False
            _log.info("ModelManager idle for >%ds — unloading CLIP", self._idle_timeout)
            return self.unload()

    def _idle_watchdog(self) -> None:
        while True:
            time.sleep(30)
            self._unload_if_idle()


_manager: ModelManager | None = None


def get_manager() -> ModelManager:
    global _manager
    with clip_scorer._lifecycle_lock:
        if _manager is None:
            _manager = ModelManager()
        return _manager
