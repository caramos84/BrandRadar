from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "BrandRadar API"
    database_url: str = "sqlite:///./brandradar.db"
    jwt_secret_key: str = "brandradar-mvp-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()
