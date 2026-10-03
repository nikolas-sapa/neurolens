from unittest.mock import patch

from PIL import Image

from app.processors.image_processor import process_image


def test_png_decode_preserves_rgb_pixels_before_scoring(tmp_path):
    path = tmp_path / "fixture.png"
    Image.new("RGBA", (3, 2), (10, 20, 30, 255)).save(path)
    with patch("app.processors.image_processor.get_brain_scores", return_value={"visual_cortex": 50}) as score:
        result = process_image(str(path))
    image = score.call_args.kwargs["image"]
    assert image.mode == "RGB"
    assert image.size == (3, 2)
    assert image.getpixel((0, 0)) == (10, 20, 30)
    assert result["type"] == "image"
