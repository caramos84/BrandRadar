from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router
from app.db.database import Base, engine
from app.models import Analysis, Asset, User  # noqa: F401


ASSET_ADDITIONAL_COLUMNS = {
    "aspect_ratio": "FLOAT",
    "pixel_area": "INTEGER",
    "visual_load_score": "FLOAT",
    "conversion_signal_score": "FLOAT",
    "text_density": "FLOAT",
    "region_count": "INTEGER",
    "text_block_count": "INTEGER",
    "cta_detected": "BOOLEAN",
    "price_detected": "BOOLEAN",
    "promo_detected": "BOOLEAN",
    "legal_detected": "BOOLEAN",
    "product_candidate_detected": "BOOLEAN",
    "logo_candidate_detected": "BOOLEAN",
    "layout_density": "FLOAT",
    "analysis_cluster_label": "VARCHAR(64)",
}


def ensure_asset_columns() -> None:
    inspector = inspect(engine)
    if "assets" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("assets")}
    with engine.begin() as connection:
        for column_name, sql_type in ASSET_ADDITIONAL_COLUMNS.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE assets ADD COLUMN {column_name} {sql_type}"))


Base.metadata.create_all(bind=engine)
ensure_asset_columns()

app = FastAPI(title="BrandRadar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_dir = Path("storage")
storage_dir.mkdir(parents=True, exist_ok=True)

app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

app.include_router(auth_router)
app.include_router(analyses_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
