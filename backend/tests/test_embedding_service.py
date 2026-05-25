from pathlib import Path

from PIL import Image

from app.services.embedding_service import generate_visual_embedding


def test_generate_visual_embedding_shape(tmp_path: Path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (64, 32), color=(120, 40, 220)).save(image_path)

    vector = generate_visual_embedding(image_path)

    assert isinstance(vector, list)
    assert len(vector) == 37
    assert all(isinstance(value, float) for value in vector)


def test_generate_visual_embedding_handles_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.png"
    vector = generate_visual_embedding(missing)
    assert vector == []
