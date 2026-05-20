from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.asset import Asset
from app.models.user import User
from app.schemas.asset import AssetAttentionResponse
from app.services.attention_diagnostic_service import run_attention_diagnostics

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/{asset_id}/attention", response_model=AssetAttentionResponse)
def get_asset_attention(asset_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = (
        db.query(Asset)
        .join(Analysis, Analysis.id == Asset.analysis_id)
        .filter(Asset.id == asset_id, Analysis.user_id == current_user.id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    preview_path = asset.preview_path or asset.stored_path
    disk_path = Path((preview_path or "").lstrip("/"))

    diag = run_attention_diagnostics(
        disk_path,
        text_block_count=asset.text_block_count,
        region_count=asset.region_count,
    )

    heatmap_url = None
    if diag["heatmap_path"] is not None:
        heatmap_url = "/" + str(diag["heatmap_path"]).replace("\\", "/").lstrip("/")

    return {
        "asset_id": asset.id,
        "heatmap_url": heatmap_url,
        "primary_focus": diag["primary_focus"],
        "secondary_focus": diag["secondary_focus"],
        "attention_dispersion": float(diag["attention_dispersion"]),
        "visual_noise": float(diag["visual_noise"]),
        "summary": diag["summary"],
    }
