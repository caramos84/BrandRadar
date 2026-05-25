from pydantic import BaseModel


class FocusZone(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    strength: float


class AssetAttentionResponse(BaseModel):
    asset_id: int
    heatmap_url: str | None
    primary_focus: FocusZone | None
    secondary_focus: list[FocusZone]
    attention_dispersion: float
    visual_noise: float
    summary: str
