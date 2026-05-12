import re
from dataclasses import dataclass
from typing import Any

CTA_TERMS = {
    "buy", "shop", "order", "discover", "learn more", "subscribe", "get", "claim", "save",
    "off", "discount", "promo", "limited", "now", "today", "compra", "ordena", "descubre",
    "conoce más", "suscríbete", "ahorra", "descuento", "oferta", "promoción", "limitado", "hoy",
}
PRICE_PROMO_TERMS = {
    "%", "2x1", "3x2", "precio", "price", "sale", "oferta", "descuento", "off", "save",
    "ahorro", "gratis", "free", "desde", "now",
}
LEGAL_TERMS = {"terms", "conditions", "legal", "aplica", "tyc", "términos", "condiciones", "restricciones"}
PRODUCT_HINTS = {"product", "producto", "pack", "bottle", "shoe", "phone", "laptop"}
LOGO_HINTS = {"logo", "brandmark", "isotype", "wordmark"}


@dataclass
class FeatureInput:
    original_filename: str
    width: int | None
    height: int | None
    size_bytes: int
    text_blocks: list[str] | None = None
    regions: list[dict[str, Any]] | None = None


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def _compute_cluster_label(conversion_signal_score: float, visual_load_score: float, product_candidate_detected: bool, text_density: float) -> str:
    if conversion_signal_score >= 65 and visual_load_score >= 60:
        return "Promotional Heavy"
    if conversion_signal_score >= 65 and visual_load_score < 60:
        return "Clean Conversion"
    if product_candidate_detected and text_density <= 0.18:
        return "Product Hero"
    if conversion_signal_score < 35 and visual_load_score < 40:
        return "Brand / Lifestyle"
    if conversion_signal_score < 65 and visual_load_score >= 60:
        return "Informational Dense"
    return "Unclassified"


def compute_asset_features(asset: FeatureInput, optional_text_blocks: list[str] | None = None, optional_regions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    text_blocks = optional_text_blocks if optional_text_blocks is not None else (asset.text_blocks or [])
    regions = optional_regions if optional_regions is not None else (asset.regions or [])

    width = asset.width or 0
    height = asset.height or 0
    pixel_area = width * height if width and height else None
    aspect_ratio = round(width / height, 4) if width and height else None

    normalized_name = re.sub(r"[_\-.]", " ", asset.original_filename.lower())
    merged_text = f"{normalized_name} {' '.join(text_blocks).lower()}"

    cta_detected = _contains_any(merged_text, CTA_TERMS)
    price_detected = _contains_any(merged_text, PRICE_PROMO_TERMS)
    promo_detected = price_detected or any(token in merged_text for token in {"promo", "discount", "sale", "oferta", "descuento"})
    legal_detected = _contains_any(merged_text, LEGAL_TERMS)
    product_candidate_detected = _contains_any(merged_text, PRODUCT_HINTS)
    logo_candidate_detected = _contains_any(merged_text, LOGO_HINTS)

    text_block_count = len(text_blocks)
    region_count = len(regions)

    if pixel_area and pixel_area > 0:
        text_density = min(1.0, (text_block_count * 45000) / pixel_area)
    else:
        text_density = 0.0

    layout_density = min(1.0, (region_count * 0.12) + (text_density * 0.6))

    area_factor = min(1.0, (pixel_area or 0) / 6_000_000)
    size_factor = min(1.0, asset.size_bytes / 4_000_000)
    visual_load_raw = (
        area_factor * 24
        + size_factor * 22
        + min(1.0, region_count / 10) * 20
        + min(1.0, text_block_count / 12) * 18
        + text_density * 16
    )
    visual_load_score = _clamp_score(visual_load_raw)

    conversion_signal_raw = (
        (18 if cta_detected else 0)
        + (20 if price_detected else 0)
        + (18 if promo_detected else 0)
        + (10 if product_candidate_detected else 0)
        + (6 if "!" in merged_text else 0)
        + min(14, text_block_count * 2)
        - (8 if legal_detected else 0)
    )
    conversion_signal_score = _clamp_score(conversion_signal_raw)

    analysis_cluster_label = _compute_cluster_label(
        conversion_signal_score=conversion_signal_score,
        visual_load_score=visual_load_score,
        product_candidate_detected=product_candidate_detected,
        text_density=text_density,
    )

    return {
        "aspect_ratio": aspect_ratio,
        "pixel_area": pixel_area,
        "visual_load_score": visual_load_score,
        "conversion_signal_score": conversion_signal_score,
        "text_density": round(text_density, 4),
        "region_count": region_count,
        "text_block_count": text_block_count,
        "cta_detected": cta_detected,
        "price_detected": price_detected,
        "promo_detected": promo_detected,
        "legal_detected": legal_detected,
        "product_candidate_detected": product_candidate_detected,
        "logo_candidate_detected": logo_candidate_detected,
        "layout_density": round(layout_density, 4),
        "analysis_cluster_label": analysis_cluster_label,
    }
