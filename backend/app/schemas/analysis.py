from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisCreateRequest(BaseModel):
    brand_name: str
    category: str
    custom_category: str | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    size_bytes: int
    stored_path: str
    preview_path: str | None
    width: int | None
    height: int | None
    created_at: datetime
    aspect_ratio: float | None
    pixel_area: int | None
    visual_load_score: float | None
    conversion_signal_score: float | None
    text_density: float | None
    region_count: int | None
    text_block_count: int | None
    cta_detected: bool | None
    price_detected: bool | None
    promo_detected: bool | None
    legal_detected: bool | None
    product_candidate_detected: bool | None
    logo_candidate_detected: bool | None
    layout_density: float | None
    analysis_cluster_label: str | None
    ocr_text: str | None
    vision_data_json: str | None
    ocr_status: str | None
    ocr_error: str | None
    embedding_json: str | None
    map_x: float | None
    map_y: float | None
    cluster_id: int | None


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    brand_name: str
    category: str
    custom_category: str | None
    status: str
    asset_count: int
    created_at: datetime
    updated_at: datetime


class AnalysisDetailResponse(AnalysisResponse):
    assets: list[AssetResponse]


class AnalysisMapPointResponse(BaseModel):
    asset_id: int
    filename: str
    preview_url: str | None
    x: float
    y: float
    cluster_id: int | None
    width: int | None
    height: int | None
    file_size: int
    aspect_ratio: float | None


class AnalysisMapResponse(BaseModel):
    analysis_id: int
    brand_name: str
    asset_count: int
    points: list[AnalysisMapPointResponse]
