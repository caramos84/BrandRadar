import json
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.analysis import Analysis
from app.models.asset import Asset
from app.models.user import User
from app.schemas.analysis import AnalysisCreateRequest, AnalysisDetailResponse, AnalysisMapResponse, AnalysisResponse, AnalysisUpdateRequest
from app.services.asset_features import FeatureInput, compute_asset_features
from app.services.asset_signals import attach_asset_signals
from app.services.layout_analysis import compute_layout_analysis
from app.services.asset_vision import analyze_image_asset, vision_data_to_json
from app.services.clustering_service import generate_analysis_map_points

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=list[AnalysisResponse])
def list_analyses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Analysis)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    analysis = Analysis(
        user_id=current_user.id,
        brand_name=payload.brand_name.strip(),
        category=payload.category.strip(),
        custom_category=(payload.custom_category or "").strip() or None,
        status="draft",
        asset_count=0,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/{analysis_id}/assets", response_model=AnalysisDetailResponse)
def upload_assets(
    analysis_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")

    analysis.status = "processing"
    db.commit()

    created_assets: list[Asset] = []

    try:
        for file in files:
            original_filename = file.filename or "uploaded-file"
            extension = original_filename.split(".")[-1].lower() if "." in original_filename else ""
            if extension not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {original_filename}")

            file_bytes = file.file.read()
            if not file_bytes:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Empty file: {original_filename}")

            stored_filename = f"{uuid4().hex}.{extension}"
            stored_path = UPLOAD_DIR / stored_filename
            stored_path.write_bytes(file_bytes)

            mime_type = file.content_type or mimetypes.guess_type(original_filename)[0] or "application/octet-stream"

            width = None
            height = None
            preview_path = None
            text_values: list[str] = []
            vision_data = {"text_blocks": [], "visual_regions": [], "ocr_status": "not_attempted", "ocr_error": None}

            if extension in {"jpg", "jpeg", "png"}:
                with Image.open(stored_path) as img:
                    width, height = img.size
                preview_path = f"/storage/uploads/{stored_filename}"
                vision_data = analyze_image_asset(stored_path)
                text_values = [
                    str(block.get("text", "")).strip()
                    for block in vision_data.get("text_blocks", [])
                    if str(block.get("text", "")).strip()
                ]

            vision_data = attach_asset_signals(vision_data)

            feature_payload = compute_asset_features(
                FeatureInput(
                    original_filename=original_filename,
                    width=width,
                    height=height,
                    size_bytes=len(file_bytes),
                    text_blocks=text_values,
                    regions=vision_data.get("visual_regions", []),
                )
            )

            allowed_feature_fields = {
                "analysis_cluster_label",
                "region_count",
                "text_block_count",
                "visual_load_score",
                "conversion_signal_score",
            }

            asset_feature_payload = {
                key: value
                for key, value in feature_payload.items()
                if key in allowed_feature_fields
            }

            asset = Asset(
                analysis_id=analysis.id,
                filename=stored_filename,
                original_filename=original_filename,
                file_type=extension,
                mime_type=mime_type,
                size_bytes=len(file_bytes),
                stored_path=f"/storage/uploads/{stored_filename}",
                preview_path=preview_path,
                width=width,
                height=height,
                ocr_text="\n".join(text_values) if text_values else None,
                vision_data_json=vision_data_to_json(vision_data),
                ocr_status=vision_data.get("ocr_status", "not_attempted"),
                ocr_error=vision_data.get("ocr_error"),
                **asset_feature_payload,
            )
            db.add(asset)
            created_assets.append(asset)

        analysis.asset_count += len(created_assets)
        analysis.status = "completed"
        db.commit()
        db.refresh(analysis)

        return analysis

    except HTTPException:
        analysis.status = "failed"
        db.commit()
        raise
    except Exception as exc:
        analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {exc}") from exc


@router.post("/{analysis_id}/recompute-features")
def recompute_features(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    assets = db.query(Asset).filter(Asset.analysis_id == analysis.id).all()
    for asset in assets:
        text_values = [line.strip() for line in (asset.ocr_text or "").splitlines() if line.strip()]

        visual_regions = []
        if asset.vision_data_json:
            try:
                vision_data = json.loads(asset.vision_data_json)
                if isinstance(vision_data, dict):
                    visual_regions = vision_data.get("visual_regions", [])
                    disk_path = Path(asset.stored_path.lstrip("/"))
                    if disk_path.exists():
                        layout_text_blocks = vision_data.get("text_blocks")
                        if not isinstance(layout_text_blocks, list):
                            layout_text_blocks = [{"text": text, "bbox": [0, 0, 0, 0]} for text in text_values]
                        vision_data["layout_analysis"] = compute_layout_analysis(
                            image_path=disk_path,
                            text_blocks=layout_text_blocks,
                            visual_regions=visual_regions,
                            attention_grid=vision_data.get("attention_grid"),
                            attention_metrics=vision_data.get("attention_metrics"),
                        )
                    asset.vision_data_json = vision_data_to_json(attach_asset_signals(vision_data))
                    if not asset.ocr_status and vision_data.get("ocr_status"):
                        asset.ocr_status = vision_data.get("ocr_status")
                    if not asset.ocr_error and vision_data.get("ocr_error"):
                        asset.ocr_error = vision_data.get("ocr_error")
            except json.JSONDecodeError:
                visual_regions = []

        features = compute_asset_features(
            FeatureInput(
                original_filename=asset.original_filename,
                width=asset.width,
                height=asset.height,
                size_bytes=asset.size_bytes,
                text_blocks=text_values,
                regions=visual_regions,
            )
        )
        for key, value in features.items():
            setattr(asset, key, value)

    db.commit()

    return {"analysis_id": analysis.id, "updated_assets": len(assets)}




@router.get("/{analysis_id}/map", response_model=AnalysisMapResponse)
def get_analysis_map(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    assets = db.query(Asset).filter(Asset.analysis_id == analysis.id).order_by(Asset.id.asc()).all()
    raw_points = generate_analysis_map_points(assets)
    points = [
        {
            "asset_id": point["asset_id"],
            "filename": point["filename"],
            "preview_url": point.get("preview_url"),
            "x": point["x"],
            "y": point["y"],
            "cluster_id": point.get("cluster_id"),
            "width": point.get("width"),
            "height": point.get("height"),
            "file_size": point["file_size"],
            "aspect_ratio": point.get("aspect_ratio"),
        }
        for point in raw_points
    ]

    point_lookup = {point["asset_id"]: point for point in points}
    for asset in assets:
        point = point_lookup.get(asset.id)
        if not point:
            continue
        asset.map_x = point["x"]
        asset.map_y = point["y"]
        asset.cluster_id = point.get("cluster_id")

    db.commit()

    return {
        "analysis_id": analysis.id,
        "brand_name": analysis.brand_name,
        "asset_count": len(assets),
        "points": points,
    }
@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.patch("/{analysis_id}", response_model=AnalysisResponse)
def update_analysis(
    analysis_id: int,
    payload: AnalysisUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    if payload.brand_name is not None:
        analysis.brand_name = payload.brand_name.strip()
    if payload.category is not None:
        analysis.category = payload.category.strip()
    if payload.custom_category is not None:
        analysis.custom_category = (payload.custom_category or "").strip() or None
    
    db.commit()
    db.refresh(analysis)
    return analysis


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
