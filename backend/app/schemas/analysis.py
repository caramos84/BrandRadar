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
