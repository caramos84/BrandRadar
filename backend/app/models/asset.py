from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pixel_area: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visual_load_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    conversion_signal_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    region_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_block_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cta_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    price_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    promo_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    legal_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    product_candidate_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    logo_candidate_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    layout_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_cluster_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ocr_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    analysis = relationship("Analysis", back_populates="assets")
