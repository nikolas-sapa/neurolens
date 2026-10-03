"""Offline lifecycle regressions, no model downloads or Torch runtime."""
import contextlib
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from app import clip_scorer, model_manager


def install_loader(monkeypatch, processor_failure=False, entered=None, release=None):
    calls = []

    class Features:
        def norm(self, **kwargs):
            return 1

        def __truediv__(self, value):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return np.ones((len(clip_scorer._FLAT_PROBES), 1))

    model = SimpleNamespace(
        eval=lambda: None,
        text_model=lambda **kwargs: (None, Features()),
        text_projection=lambda pooled: pooled,
    )

    def load_model(model_id):
        calls.append(model_id)
        if entered:
            entered.set()
            assert release.wait(2)
        return model

    failures = [processor_failure]

    def load_processor(model_id):
        should_fail = failures.pop() if failures else False
        if should_fail:
            raise RuntimeError("processor unavailable")
        return lambda **kwargs: {}

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(no_grad=contextlib.nullcontext))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        CLIPModel=SimpleNamespace(from_pretrained=load_model),
        CLIPProcessor=SimpleNamespace(from_pretrained=load_processor),
    ))
    return calls


def test_failed_load_leaves_no_partial_state_and_retry_loads_twice(monkeypatch):
    calls = install_loader(monkeypatch, processor_failure=True)
    scorer = clip_scorer.CLIPScorer()
    with pytest.raises(RuntimeError, match="processor unavailable"):
        scorer.load()
    assert not scorer.loaded
    assert scorer._model is None
    assert scorer._processor is None
    assert scorer._probe_features is None
    scorer.load()
    assert scorer.loaded
    assert len(calls) == 2


def test_concurrent_load_initializes_exactly_once(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    calls = install_loader(monkeypatch, entered=entered, release=release)
    scorer = clip_scorer.CLIPScorer()
    errors = []

    def load():
        try:
            scorer.load()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=load) for _ in range(4)]
    for thread in threads:
        thread.start()
    assert entered.wait(2)
    release.set()
    for thread in threads:
        thread.join(2)
        assert not thread.is_alive()
    assert not errors
    assert len(calls) == 1


def manager_without_watchdog(monkeypatch, scorer):
    monkeypatch.setattr(clip_scorer, "_scorer", scorer)
    with monkeypatch.context() as patch:
        patch.setattr(threading.Thread, "start", lambda self: None)
        return model_manager.ModelManager(idle_timeout=1)


def loaded_scorer():
    scorer = clip_scorer.CLIPScorer()
    scorer._model = object()
    scorer._processor = object()
    scorer._probe_features = np.ones((len(clip_scorer._FLAT_PROBES), 1))
    return scorer


@pytest.mark.parametrize("modality", ["text", "image"])
def test_real_score_updates_idle_activity_and_expired_unloads_once(monkeypatch, modality):
    scorer = loaded_scorer()
    mgr = manager_without_watchdog(monkeypatch, scorer)
    monkeypatch.setattr(scorer, f"_embed_{modality}", lambda value: np.ones(1))
    mgr._last_used = time.monotonic() - 5
    getattr(scorer, f"score_{modality}")("copy")
    assert mgr.status()["idle_for_seconds"] < 1
    assert mgr._unload_if_idle() is False
    mgr._last_used = time.monotonic() - 5
    assert mgr._unload_if_idle() is True
    assert mgr._unload_if_idle() is False


@pytest.mark.parametrize("operation", ["unload", "idle"])
def test_unload_waits_for_active_score_and_idle_keeps_completed_score(monkeypatch, operation):
    scorer = loaded_scorer()
    mgr = manager_without_watchdog(monkeypatch, scorer)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    errors, result = [], []
    mgr._last_used = time.monotonic() - 5

    def embed(text):
        entered.set()
        assert release.wait(2)
        assert scorer._model is not None
        return np.ones(1)

    monkeypatch.setattr(scorer, "_embed_text", embed)

    def score():
        try:
            result.append(scorer.score_text("copy"))
        except Exception as exc:
            errors.append(exc)

    def unload():
        try:
            if operation == "idle":
                mgr._unload_if_idle()
            else:
                mgr.unload()
        except Exception as exc:
            errors.append(exc)
        finally:
            finished.set()

    scoring = threading.Thread(target=score)
    unloading = threading.Thread(target=unload)
    scoring.start()
    assert entered.wait(2)
    unloading.start()
    assert not finished.wait(0.05)
    release.set()
    scoring.join(2)
    unloading.join(2)
    assert not scoring.is_alive() and not unloading.is_alive()
    assert not errors
    assert len(result) == 1
    assert scorer.loaded is (operation == "idle")


def test_score_inputs_initializes_watchdog_once_from_fresh_manager(monkeypatch):
    scorer = loaded_scorer()
    monkeypatch.setattr(clip_scorer, "_scorer", scorer)
    monkeypatch.setattr(model_manager, "_manager", None)
    monkeypatch.setattr(scorer, "_embed_text", lambda text: np.ones(1))
    started = []
    monkeypatch.setattr(threading.Thread, "start", lambda thread: started.append(thread))

    first = clip_scorer.score_inputs(texts=["first"])
    second = clip_scorer.score_inputs(texts=["second"])

    assert first == second == {region: 100 for region in clip_scorer.REGION_PROBES}
    assert model_manager._manager is not None
    assert len(started) == 1
    assert started[0] is model_manager._manager._watchdog
    assert started[0].daemon
    assert model_manager._manager.status()["idle_for_seconds"] < 1
