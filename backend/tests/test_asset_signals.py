from app.services.asset_signals import attach_asset_signals, compute_asset_signals


REQUIRED_SIGNAL_KEYS = {
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

    assert set(signals) == REQUIRED_SIGNAL_KEYS
    assert all(0.0 <= value <= 100.0 for value in signals.values())
    assert signals["promo_presence"] >= 80.0
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
    assert set(updated["asset_signals"]) == REQUIRED_SIGNAL_KEYS


def test_focused_simple_brand_asset_does_not_saturate_attention_dispersion():
    signals = compute_asset_signals(
        text_blocks=[{"text": "Marca", "bbox": [30, 30, 60, 20]}],
        visual_regions=[{"bbox": [20, 20, 180, 180]}],
        attention_grid=[
            [0.02, 0.05, 0.02],
            [0.04, 0.95, 0.06],
            [0.01, 0.04, 0.02],
        ],
        attention_metrics={
            "focus_clarity": 0.86,
            "visual_noise": 0.12,
            "primary_attention_score": 0.95,
            "top3_attention_mean": 0.36,
        },
    )

    assert 20.0 <= signals["attention_dispersion"] <= 45.0
    assert signals["brand_signal_clarity"] > signals["layout_density"]


def test_financing_cuotas_cta_copy_has_language_stress_and_conversion_intent():
    signals = compute_asset_signals(
        text_blocks=[{"text": "Compra en 12 cuotas paga desde hoy aplica condiciones", "bbox": [0, 0, 300, 30]}],
        visual_regions=[{"bbox": [0, 0, 320, 200]}, {"bbox": [20, 120, 120, 70]}],
        attention_grid=[[0.1, 0.3, 0.2], [0.2, 0.5, 0.4]],
        attention_metrics={
            "focus_clarity": 0.48,
            "visual_noise": 0.38,
            "primary_attention_score": 0.5,
            "top3_attention_mean": 0.4,
        },
    )

    assert signals["language_stress"] >= 35.0
    assert 40.0 <= signals["conversion_intent"] <= 75.0
    assert signals["commercial_pressure"] >= signals["conversion_intent"]


def test_multi_panel_asset_with_many_regions_has_moderate_layout_density():
    signals = compute_asset_signals(
        text_blocks=[
            {"text": "Card 1", "bbox": [10, 10, 80, 20]},
            {"text": "Card 2", "bbox": [210, 10, 80, 20]},
            {"text": "Card 3", "bbox": [410, 10, 80, 20]},
        ],
        visual_regions=[
            {"bbox": [0, 0, 180, 260]},
            {"bbox": [200, 0, 180, 260]},
            {"bbox": [400, 0, 180, 260]},
            {"bbox": [20, 180, 80, 50]},
            {"bbox": [220, 180, 80, 50]},
            {"bbox": [420, 180, 80, 50]},
        ],
        attention_grid=[
            [0.6, 0.5, 0.2, 0.6, 0.5, 0.2, 0.6, 0.5, 0.2],
            [0.4, 0.3, 0.1, 0.4, 0.3, 0.1, 0.4, 0.3, 0.1],
        ],
        attention_metrics={"focus_clarity": 0.4, "visual_noise": 0.42, "primary_attention_score": 0.6, "top3_attention_mean": 0.6},
    )

    assert 35.0 <= signals["layout_density"] <= 70.0
    assert 45.0 <= signals["attention_dispersion"] <= 75.0


def test_promo_cta_has_higher_conversion_intent_than_lifestyle_copy():
    promo = compute_asset_signals(
        text_blocks=[{"text": "Compra hoy descuentos exclusivos 30% OFF", "bbox": [0, 0, 300, 30]}],
        visual_regions=[{"bbox": [0, 0, 360, 180]}],
    )
    lifestyle = compute_asset_signals(
        text_blocks=[{"text": "Inspiración para tu día", "bbox": [0, 0, 200, 30]}],
        visual_regions=[{"bbox": [0, 0, 360, 180]}],
    )

    assert promo["conversion_intent"] >= lifestyle["conversion_intent"] + 35.0
    assert lifestyle["conversion_intent"] < 20.0


def test_aprovecha_descuentos_exclusivos_ocr_scores_as_commercial():
    signals = compute_asset_signals(
        text_blocks=[{"text": "Aprovecha descuentos exclusivos +60 marcas aliadas Rddi"}],
    )

    assert signals["promo_presence"] > 40.0
    assert signals["commercial_pressure"] > 30.0
    assert signals["conversion_intent"] > 25.0


def test_black_friday_cuotas_credito_ocr_scores_as_commercial_and_stressful():
    signals = compute_asset_signals(
        text_blocks=[{"text": "Black Friday 6 cuotas 12 cuotas Págala a crédito"}],
    )

    assert signals["promo_presence"] > 50.0
    assert signals["commercial_pressure"] > 35.0
    assert signals["conversion_intent"] > 30.0
    assert signals["language_stress"] > 12.0


def test_dcto_compra_ocr_keeps_strong_promo_and_conversion_signal():
    signals = compute_asset_signals(
        text_blocks=[{"text": "200 de dcto. en tu compra Con Addi"}],
    )

    assert signals["promo_presence"] >= 80.0
    assert signals["conversion_intent"] >= 30.0
