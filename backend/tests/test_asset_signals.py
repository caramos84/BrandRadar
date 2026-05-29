from app.services.asset_signals import attach_asset_signals, compute_asset_signals


def test_compute_asset_signals_returns_required_scores():
    signals = compute_asset_signals(
        text_blocks=[
            {"text": "Compra hoy 20% OFF", "bbox": [10, 10, 120, 24]},
            {"text": "Logo Marca", "bbox": [20, 70, 90, 20]},
        ],
        visual_regions=[
            {"bbox": [0, 0, 200, 120]},
            {"bbox": [220, 80, 120, 90]},
        ],
        attention_grid=[[0.1, 0.8], [0.2, 0.4]],
        attention_metrics={"attention_dispersion": 0.62, "focus_clarity": 0.7, "visual_noise": 0.3},
    )

    assert set(signals) == {
        "visual_load",
        "conversion_intent",
        "language_stress",
        "layout_density",
        "attention_dispersion",
        "brand_signal_clarity",
        "text_density",
        "promo_presence",
        "hierarchy_clarity",
        "commercial_pressure",
    }
    assert all(0.0 <= value <= 100.0 for value in signals.values())
    assert signals["promo_presence"] == 100.0
    assert signals["conversion_intent"] > 0.0


def test_attach_asset_signals_preserves_existing_vision_data():
    vision_data = {
        "text_blocks": [{"text": "Oferta limitada", "bbox": [0, 0, 100, 20]}],
        "visual_regions": [],
        "attention_grid": [],
        "attention_metrics": {"attention_dispersion": 0.5},
        "attention_heatmap_path": "/storage/uploads/example_attention_heatmap.png",
    }

    updated = attach_asset_signals(vision_data)

    assert updated["attention_heatmap_path"] == "/storage/uploads/example_attention_heatmap.png"
    assert updated["asset_signals"]["attention_dispersion"] == 50.0
