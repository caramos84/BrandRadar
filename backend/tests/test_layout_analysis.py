import json
import struct

from app.services.layout_analysis import compute_layout_analysis


def _png_path(tmp_path, width=400, height=300):
    path = tmp_path / "asset.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00")
    return path


def test_layout_analysis_schema_is_json_serializable(tmp_path):
    path = _png_path(tmp_path)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[{"text": "Compra ahora", "bbox": [40, 220, 120, 28], "confidence": 90}],
        visual_regions=[{"bbox": [20, 30, 260, 170], "confidence": 0.7}],
        attention_metrics={"focus_clarity": 0.6},
    )

    json.dumps(result)
    assert result["version"] == 1
    assert result["image"] == {"width_px": 400, "height_px": 300}
    assert set(result) == {"version", "image", "summary", "blocks", "artifacts", "reading"}
    assert set(result["summary"]) == {
        "framework",
        "composition",
        "dominant_element",
        "layout_complexity",
        "focus_behavior",
        "commercial_structure",
        "hierarchy",
        "block_count",
    }
    assert set(result["artifacts"]) == {"layout_overlay_path", "layout_wireframe_path"}
    assert isinstance(result["reading"], str)


def test_visual_region_generates_normalized_and_pixel_measurements(tmp_path):
    path = _png_path(tmp_path, width=400, height=200)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[],
        visual_regions=[{"bbox": [40, 20, 120, 80], "confidence": 0.8}],
    )

    block = result["blocks"][0]
    assert block["x_px"] == 40
    assert block["y_px"] == 20
    assert block["width_px"] == 120
    assert block["height_px"] == 80
    assert block["x"] == 0.1
    assert block["y"] == 0.1
    assert block["width"] == 0.3
    assert block["height"] == 0.4
    assert block["area_pct"] == 12.0
    assert 0.0 <= block["confidence"] <= 1.0
    assert block["source"] == "visual"


def test_invalid_ocr_bbox_does_not_create_spatial_block(tmp_path):
    path = _png_path(tmp_path)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[{"text": "Black Friday 12 cuotas", "bbox": [0, 0, 0, 0]}],
        visual_regions=[],
    )

    assert result["blocks"] == []
    assert result["summary"]["block_count"] == 0


def test_price_offer_text_classifies_overlapping_spatial_block(tmp_path):
    path = _png_path(tmp_path)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[{"text": "Black Friday 12 cuotas descuento", "bbox": [60, 60, 220, 36]}],
        visual_regions=[{"bbox": [40, 40, 280, 110], "confidence": 0.6}],
    )

    assert result["blocks"][0]["type"] == "Price / Offer"
    assert result["blocks"][0]["source"] == "combined"


def test_cta_text_classifies_overlapping_spatial_block(tmp_path):
    path = _png_path(tmp_path)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[{"text": "Aprovecha y recibe", "bbox": [80, 190, 170, 32]}],
        visual_regions=[{"bbox": [60, 170, 220, 70], "confidence": 0.5}],
    )

    assert result["blocks"][0]["type"] == "CTA"
    assert result["blocks"][0]["source"] == "combined"


def test_bottom_small_region_can_be_legal_footer(tmp_path):
    path = _png_path(tmp_path, width=400, height=300)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[],
        visual_regions=[{"bbox": [20, 255, 330, 28], "confidence": 0.4}],
    )

    assert result["blocks"][0]["type"] == "Legal / Footer"


def test_artifact_generation_failure_does_not_crash(tmp_path):
    path = _png_path(tmp_path)
    result = compute_layout_analysis(
        image_path=path,
        text_blocks=[],
        visual_regions=[{"bbox": [20, 20, 120, 100], "confidence": 0.8}],
    )

    assert result["artifacts"] == {"layout_overlay_path": None, "layout_wireframe_path": None}
    assert result["blocks"]
