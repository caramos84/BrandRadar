from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router
from app.db.database import Base, engine
from app.models import Analysis, Asset, User  # noqa: F401

Base.metadata.create_all(bind=engine)

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
