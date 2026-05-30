import json

from app.services.linguistic_stress import compute_linguistic_stress


def _dense_blocks():
    return [
        {"text": "LIMITED TIME OFFER SAVE BIG NOW", "bbox": [20, 20, 340, 40]},
        {
            "text": "Terms and conditions apply. Drink responsibly. Copyright trademark restrictions apply in all participating stores.",
            "bbox": [20, 250, 360, 36],
        },
    ]


def _layout():
    return {
        "blocks": [
            {"type": "Headline", "x_px": 20, "y_px": 20, "width_px": 340, "height_px": 40, "area_pct": 5.0},
            {"type": "Legal / Footer", "x_px": 20, "y_px": 250, "width_px": 360, "height_px": 36, "area_pct": 3.2},
        ]
    }


def test_linguistic_stress_schema_is_json_serializable():
    result = compute_linguistic_stress(_dense_blocks(), _layout())

    json.dumps(result)
    assert result["version"] == 1
    assert result["baseline_language"] == "en"
    assert set(result) == {"version", "baseline_language", "baseline", "languages", "summary", "reading"}
    assert result["baseline"]["total_chars"] > 0
    assert set(result["baseline"]["sections"]) == {"headline", "body", "legal", "cta", "price_offer", "other"}
    assert isinstance(result["reading"], str)


def test_all_seven_target_languages_are_present():
    result = compute_linguistic_stress(_dense_blocks(), _layout())

    assert [language["code"] for language in result["languages"]] == ["es", "pt", "de", "fr", "ja", "ko", "zh"]


def test_german_and_french_can_exceed_120_for_dense_headline_and_legal():
    result = compute_linguistic_stress(_dense_blocks(), _layout())
    by_code = {language["code"]: language for language in result["languages"]}

    assert by_code["de"]["expansion_pct"] > 120.0
    assert by_code["fr"]["expansion_pct"] > 120.0
    assert by_code["de"]["status"] == "critical"
    assert by_code["fr"]["status"] == "critical"


def test_cjk_languages_have_lower_expansion_than_german_and_french():
    result = compute_linguistic_stress(_dense_blocks(), _layout())
    by_code = {language["code"]: language for language in result["languages"]}

    for code in ["ja", "ko", "zh"]:
        assert by_code[code]["expansion_pct"] < by_code["de"]["expansion_pct"]
        assert by_code[code]["expansion_pct"] < by_code["fr"]["expansion_pct"]


def test_long_legal_section_has_high_layout_risk():
    result = compute_linguistic_stress(_dense_blocks(), _layout())
    de_legal = next(language for language in result["languages"] if language["code"] == "de")["sections"]["legal"]

    assert de_legal["status"] == "critical"
    assert de_legal["layout_risk"] == "high"


def test_missing_layout_analysis_still_returns_valid_output():
    result = compute_linguistic_stress([{"text": "Buy now and save 20%. Terms apply."}], None)

    assert len(result["languages"]) == 7
    assert result["baseline"]["total_chars"] > 0
    assert result["summary"]["overall_status"] in {"green", "amber", "red"}


def test_invalid_or_empty_text_blocks_return_safe_output():
    result = compute_linguistic_stress([{"text": "", "bbox": [0, 0, 0, 0]}], _layout())

    assert result["languages"] == []
    assert result["summary"] == {
        "overall_status": "unknown",
        "critical_languages": [],
        "warning_languages": [],
        "comfortable_languages": [],
        "worst_language": None,
        "max_expansion_pct": 0,
        "primary_risk_sections": [],
    }
    assert result["reading"] == ""


def test_recommendations_are_produced_for_critical_languages():
    result = compute_linguistic_stress(_dense_blocks(), _layout())
    critical_languages = [language for language in result["languages"] if language["status"] == "critical"]

    assert critical_languages
    assert all(language["recommendations"] for language in critical_languages)


def test_normal_copy_keeps_german_expansion_within_reasonable_cap():
    result = compute_linguistic_stress([
        {"text": "Fresh flavor for every day", "bbox": [20, 20, 260, 42]},
        {"text": "Shop now", "bbox": [20, 90, 90, 28]},
    ])
    german = next(language for language in result["languages"] if language["code"] == "de")

    assert german["expansion_pct"] <= 140.0
    assert german["expansion_pct"] >= 135.0


def test_language_expansion_relative_ordering_is_stable():
    result = compute_linguistic_stress([{"text": "Fresh flavor for every day", "bbox": [20, 20, 260, 42]}])
    by_code = {language["code"]: language["expansion_pct"] for language in result["languages"]}

    assert by_code["zh"] < by_code["ko"] < by_code["ja"] < by_code["es"] < by_code["pt"] < by_code["fr"] < by_code["de"]


def test_status_thresholds_remain_ok_warning_and_critical():
    result = compute_linguistic_stress([{"text": "Simple headline", "bbox": [20, 20, 180, 40]}])
    by_code = {language["code"]: language for language in result["languages"]}

    assert by_code["zh"]["status"] == "ok"
    assert by_code["es"]["status"] == "warning"
    assert by_code["de"]["status"] == "critical"
