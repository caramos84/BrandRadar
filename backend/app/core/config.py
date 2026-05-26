import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "BrandRadar API"
    database_url: str = "sqlite:///./brandradar.db"
    jwt_secret_key: str = "brandradar-mvp-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ocr_space_api_key: str | None = None
    ocr_space_endpoint: str = "https://api.ocr.space/parse/image"
    ocr_provider: str = "auto"


settings = Settings(
    app_name=os.getenv("APP_NAME", "BrandRadar API"),
    database_url=os.getenv("DATABASE_URL", "sqlite:///./brandradar.db"),
    jwt_secret_key=os.getenv("JWT_SECRET_KEY", "brandradar-mvp-secret-change-me"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
    ocr_space_api_key=os.getenv("OCR_SPACE_API_KEY"),
    ocr_space_endpoint=os.getenv("OCR_SPACE_ENDPOINT", "https://api.ocr.space/parse/image"),
    ocr_provider=os.getenv("OCR_PROVIDER", "auto"),
)
