import numpy as np
import pytest
from PIL import Image

from app import clip_scorer
from app.clip_scorer import (
    CLIPScorer, REGION_PROBES, _normalize, score_inputs,
)


def _make_image() -> Image.Image:
    return Image.fromarray(np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8))


def test_region_probes_has_eight_entries():
    assert len(REGION_PROBES) == 8
    expected = {"visual_cortex", "face_social", "amygdala", "hippocampus",
                "language_areas", "reward_circuit", "prefrontal", "motor_action"}
    assert set(REGION_PROBES.keys()) == expected


def test_every_region_has_at_least_two_probes():
    for region, probes in REGION_PROBES.items():
        assert len(probes) >= 2, f"{region} has too few probes"


def test_normalize_low_clamps_to_zero():
    # Default window is image: [0.15, 0.25]
    assert _normalize(0.0) == 0
    assert _normalize(0.10) == 0


def test_normalize_high_clamps_to_hundred():
    assert _normalize(0.50) == 100
    assert _normalize(0.99) == 100


def test_normalize_midpoint():
    # Image window midpoint is 0.20; test with explicit window for clarity
    assert 49 <= _normalize(0.20, 0.15, 0.25) <= 51


def test_score_from_embedding_returns_all_eight_regions():  # CLAUDE_SECRET_ALLOW
    scorer = CLIPScorer()
    n_probes = sum(len(p) for p in REGION_PROBES.values())
    scorer._probe_features = np.random.randn(n_probes, 512)
    scorer._probe_features /= np.linalg.norm(scorer._probe_features, axis=-1, keepdims=True)
    embedding = np.random.randn(512)
    embedding /= np.linalg.norm(embedding)
    scores = scorer._score_from_embedding(embedding)
    assert set(scores.keys()) == set(REGION_PROBES.keys())
    assert all(0 <= v <= 100 for v in scores.values())


def test_score_inputs_requires_at_least_one(monkeypatch):  # CLAUDE_SECRET_ALLOW
    with pytest.raises(ValueError, match="requires at least one"):
        score_inputs()


def test_score_inputs_averages_over_inputs(monkeypatch):  # CLAUDE_SECRET_ALLOW
    fake = clip_scorer.CLIPScorer()
    monkeypatch.setattr(fake, "load", lambda: None)
    fake.score_image = lambda img: {k: 80 for k in REGION_PROBES}
    fake.score_text = lambda t: {k: 40 for k in REGION_PROBES}
    monkeypatch.setattr(clip_scorer, "_scorer", fake)

    result = score_inputs(images=[_make_image()], texts=["copy"])
    assert all(v == 60 for v in result.values())


def test_score_inputs_skips_blank_text(monkeypatch):  # CLAUDE_SECRET_ALLOW
    fake = clip_scorer.CLIPScorer()
    monkeypatch.setattr(fake, "load", lambda: None)
    fake.score_image = lambda img: {k: 70 for k in REGION_PROBES}
    fake.score_text = lambda t: {k: 30 for k in REGION_PROBES}
    monkeypatch.setattr(clip_scorer, "_scorer", fake)

    result = score_inputs(images=[_make_image()], texts=["", "  "])
    assert all(v == 70 for v in result.values())


def test_score_from_embedding_raises_if_not_loaded():  # CLAUDE_SECRET_ALLOW
    scorer = CLIPScorer()
    with pytest.raises(RuntimeError, match="Probe features not initialized"):
        scorer._score_from_embedding(np.zeros(512))


def test_unload_resets_state():
    scorer = CLIPScorer()
    scorer._model = object()
    scorer._processor = object()
    scorer._probe_features = np.zeros((1, 512))
    assert scorer.unload() is True
    assert not scorer.loaded
    assert scorer._probe_features is None


def test_unload_when_not_loaded_returns_false():
    scorer = CLIPScorer()
    assert scorer.unload() is False
