from pathlib import Path

import cv2
import numpy as np

from app.services.attention_diagnostic_service import run_attention_diagnostics


def test_attention_scores_range(tmp_path: Path):
    image = np.zeros((200, 300, 3), dtype=np.uint8)
    cv2.rectangle(image, (40, 50), (180, 160), (255, 255, 255), -1)
    p = tmp_path / "sample.jpg"
    cv2.imwrite(str(p), image)

    result = run_attention_diagnostics(p, text_block_count=3, region_count=4)

    assert 0.0 <= result["attention_dispersion"] <= 1.0
    assert 0.0 <= result["visual_noise"] <= 1.0
    assert result["heatmap_path"] is not None


def test_attention_missing_preview_graceful(tmp_path: Path):
    result = run_attention_diagnostics(tmp_path / "missing.jpg")
    assert result["heatmap_path"] is None
    assert result["primary_focus"] is None
    assert result["secondary_focus"] == []
