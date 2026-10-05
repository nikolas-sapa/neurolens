"""CLIP-based brain region scoring.

Replaces the Apple-Silicon-only mlx-vlm Qwen2-VL scorer with a portable CLIP
ViT-L/14 backbone. Each brain region has a small set of probe texts; the score
is the cosine similarity between the input embedding and the best-matching
probe, linearly mapped from a calibrated reference range to 0-100.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Iterable, Sequence

import numpy as np
from PIL import Image

_log = logging.getLogger(__name__)

# One model lifecycle: initialization, inference, eviction and activity are atomic.
_lifecycle_lock = threading.RLock()
_last_used: float = 0.0

CLIP_MODEL_ID = "openai/clip-vit-large-patch14"

# Per-region probe texts. Each list captures what *activates* that brain region.
# CLIP scores the input against every probe; we take the max similarity per region.
REGION_PROBES: dict[str, list[str]] = {
    "visual_cortex": [
        "vibrant colors and rich visual composition",
        "high contrast and striking aesthetic",
        "sharp detailed photograph with strong lighting",
        "clean professional design with strong visual hierarchy",
    ],
    "face_social": [
        "a human face making direct eye contact",
        "people smiling and connecting with each other",
        "warm community of people together",
        "a person speaking authentically to camera",
    ],
    "amygdala": [
        "intense emotional moment with high stakes",
        "urgent dramatic scene that grabs attention",
        "exciting aspirational lifestyle imagery",
        "fearful or alarming situation",
    ],
    "hippocampus": [
        "novel surprising scene that stands out",
        "memorable distinctive imagery with story",
        "unique creative concept with twist",
        "iconic recognizable brand moment",
    ],
    "language_areas": [
        "clear bold headline text and persuasive copy",
        "easy to read messaging with strong value proposition",
        "compelling tagline that promises a benefit",
        "well-structured product description",
    ],
    "reward_circuit": [
        "luxurious premium product with desirable feel",
        "exclusive aspirational item people want",
        "transformation before and after result",
        "satisfying payoff moment with reward",
    ],
    "prefrontal": [
        "data charts and statistics proving results",
        "trustworthy professional credentials and proof",
        "logical comparison with reasons to believe",
        "expert authority figure giving advice",
    ],
    "motor_action": [
        "dynamic movement and energetic action",
        "clear call to action button telling viewer to act now",
        "fast paced kinetic motion with urgency",
        "athletic powerful physical action",
    ],
}

# CLIP ViT-L/14 cosine similarities differ by modality:
#   - image vs probe-text: typically [0.15, 0.25]  (cross-modal, narrower band)
#   - text  vs probe-text: typically [0.64, 0.74]  (in-modality, narrower than B/32)
# Linearly map the modality-appropriate window to [0, 100] and clip.
_IMAGE_SIM_LOW, _IMAGE_SIM_HIGH = 0.15, 0.25
_TEXT_SIM_LOW, _TEXT_SIM_HIGH = 0.64, 0.74


def _normalize(sim: float, low: float = _IMAGE_SIM_LOW, high: float = _IMAGE_SIM_HIGH) -> int:
    if sim <= low:
        return 0
    if sim >= high:
        return 100
    return int(round((sim - low) / (high - low) * 100))


def _flatten_probes() -> tuple[list[str], list[tuple[str, int]]]:
    """Return (all_probe_texts, [(region_key, probe_index_within_region)])."""
    flat: list[str] = []
    index: list[tuple[str, int]] = []
    for region, probes in REGION_PROBES.items():
        for i, p in enumerate(probes):
            flat.append(p)
            index.append((region, i))
    return flat, index


_FLAT_PROBES, _PROBE_INDEX = _flatten_probes()


class CLIPScorer:
    """Wraps a HuggingFace CLIPModel + CLIPProcessor with cached probe embeddings."""

    def __init__(self, model_id: str = CLIP_MODEL_ID):
        self._model_id = model_id
        self._model = None
        self._processor = None
        self._probe_features: np.ndarray | None = None  # (n_probes, dim)

    def load(self) -> None:
        global _last_used
        with _lifecycle_lock:
            if self._model is not None:
                return
            import torch
            from transformers import CLIPModel, CLIPProcessor

            _log.info("Loading CLIP %s", self._model_id)
            model = CLIPModel.from_pretrained(self._model_id)
            model.eval()
            processor = CLIPProcessor.from_pretrained(self._model_id)

            with torch.no_grad():
                inputs = processor(text=_FLAT_PROBES, return_tensors="pt", padding=True)
                text_outputs = model.text_model(**inputs)
                features = model.text_projection(text_outputs[1])
                features = features / features.norm(dim=-1, keepdim=True)
                probe_features = features.cpu().numpy()

            # Failed initialization never leaves a partially loaded singleton.
            self._processor = processor
            self._probe_features = probe_features
            self._model = model
            _last_used = time.monotonic()

    def unload(self) -> bool:
        with _lifecycle_lock:
            if self._model is None:
                return False
            self._model = None
            self._processor = None
            self._probe_features = None
            import gc
            gc.collect()
            return True

    @property
    def loaded(self) -> bool:
        with _lifecycle_lock:
            return self._model is not None

    def _encode_text(self, inputs):
        """Manual text projection — bypasses broken get_text_features in some
        transformers versions. Returns (n, projection_dim) L2-normalized."""
        text_outputs = self._model.text_model(**inputs)
        pooled = text_outputs[1]  # pooler_output
        embeds = self._model.text_projection(pooled)
        return embeds / embeds.norm(dim=-1, keepdim=True)

    def _encode_image(self, inputs):
        """Manual image projection. Returns (n, projection_dim) L2-normalized."""
        vision_outputs = self._model.vision_model(pixel_values=inputs["pixel_values"])
        pooled = vision_outputs[1]  # pooler_output
        embeds = self._model.visual_projection(pooled)
        return embeds / embeds.norm(dim=-1, keepdim=True)

    def _embed_image(self, image: Image.Image) -> np.ndarray:
        import torch
        with torch.no_grad():
            inputs = self._processor(images=image.convert("RGB"), return_tensors="pt")
            features = self._encode_image(inputs)
            return features.cpu().numpy()[0]

    def _embed_text(self, text: str) -> np.ndarray:
        import torch
        with torch.no_grad():
            inputs = self._processor(
                text=[text[:1500]], return_tensors="pt", padding=True, truncation=True
            )
            features = self._encode_text(inputs)
            return features.cpu().numpy()[0]

    def _score_from_embedding(
        self,
        embedding: np.ndarray,
        low: float = _IMAGE_SIM_LOW,
        high: float = _IMAGE_SIM_HIGH,
    ) -> dict[str, int]:
        if self._probe_features is None:
            raise RuntimeError("Probe features not initialized — call load() first")
        sims = self._probe_features @ embedding  # (n_probes,)
        per_region: dict[str, float] = {r: -1.0 for r in REGION_PROBES}
        for sim, (region, _) in zip(sims, _PROBE_INDEX):
            if sim > per_region[region]:
                per_region[region] = float(sim)
        return {region: _normalize(sim, low, high) for region, sim in per_region.items()}

    def score_image(self, image: Image.Image) -> dict[str, int]:
        global _last_used
        with _lifecycle_lock:
            self.load()
            try:
                return self._score_from_embedding(
                    self._embed_image(image), _IMAGE_SIM_LOW, _IMAGE_SIM_HIGH
                )
            finally:
                _last_used = time.monotonic()

    def score_text(self, text: str) -> dict[str, int]:
        global _last_used
        with _lifecycle_lock:
            self.load()
            try:
                return self._score_from_embedding(
                    self._embed_text(text), _TEXT_SIM_LOW, _TEXT_SIM_HIGH
                )
            finally:
                _last_used = time.monotonic()


_scorer: CLIPScorer | None = None


def get_scorer() -> CLIPScorer:
    global _scorer
    with _lifecycle_lock:
        if _scorer is None:
            _scorer = CLIPScorer()
        return _scorer


def score_inputs(
    images: Sequence[Image.Image] | None = None,
    texts: Iterable[str] | None = None,
) -> dict[str, int]:
    """Score one or more images and/or texts. Per-region scores are averaged."""
    images = list(images or [])
    texts = list(texts or [])
    if not images and not texts:
        raise ValueError("score_inputs requires at least one image or text input")

    # Runtime import avoids the manager/scorer import cycle.
    from app.model_manager import get_manager

    scorer, _ = get_manager().get()
    region_keys = list(REGION_PROBES.keys())
    accum: dict[str, list[int]] = {k: [] for k in region_keys}

    for img in images:
        for k, v in scorer.score_image(img).items():
            accum[k].append(v)
    for t in texts:
        if t.strip():
            for k, v in scorer.score_text(t).items():
                accum[k].append(v)

    return {
        k: int(round(sum(vs) / len(vs))) if vs else 50
        for k, vs in accum.items()
    }
