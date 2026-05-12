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
from app.schemas.analysis import AnalysisCreateRequest, AnalysisDetailResponse, AnalysisResponse
from app.services.asset_features import FeatureInput, compute_asset_features
from app.services.asset_vision import analyze_image_asset, vision_data_to_json

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
                **feature_payload,
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


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(analysis_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis
