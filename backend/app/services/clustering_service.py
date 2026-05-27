from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from app.models.asset import Asset
from app.services.embedding_service import generate_visual_embedding


def _normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    lo = float(values.min())
    hi = float(values.max())
    if np.isclose(lo, hi):
        return np.full_like(values, 50.0, dtype=np.float32)
    return ((values - lo) / (hi - lo) * 100.0).astype(np.float32)


def _fallback_point(asset: Asset) -> dict:
    x = asset.conversion_signal_score
    if x is None:
        x = min(max((asset.aspect_ratio or 1.0) * 20.0, 0.0), 100.0)

    y = asset.visual_load_score
    if y is None:
        y = min(max(np.log1p(asset.size_bytes) * 6.0, 0.0), 100.0)

    return {"x": float(x), "y": float(y), "cluster_id": 0, "status": "fallback"}


def generate_analysis_map_points(assets: list[Asset]) -> list[dict]:
    if not assets:
        return []

    vector_rows: list[np.ndarray] = []
    vector_assets: list[Asset] = []
    fallback_assets: list[Asset] = []

    for asset in assets:
        embedding: list[float] = []
        if asset.embedding_json:
            try:
                parsed = json.loads(asset.embedding_json)
                if isinstance(parsed, list) and parsed:
                    embedding = [float(v) for v in parsed]
            except (TypeError, ValueError, json.JSONDecodeError):
                embedding = []

        if not embedding and asset.file_type.lower() in {"jpg", "jpeg", "png"}:
            disk_path = Path(asset.stored_path.lstrip("/"))
            if disk_path.exists():
                embedding = generate_visual_embedding(disk_path)

        if embedding:
            asset.embedding_json = json.dumps(embedding)
            vector_rows.append(np.asarray(embedding, dtype=np.float32))
            vector_assets.append(asset)
        else:
            fallback_assets.append(asset)

    points: dict[int, dict] = {}

    if len(vector_assets) < 2:
        for asset in vector_assets + fallback_assets:
            points[asset.id] = _fallback_point(asset)
    else:
        try:
            matrix = np.vstack(vector_rows)
            pca = PCA(n_components=2, random_state=42)
            coords = pca.fit_transform(matrix)

            xs = _normalize(coords[:, 0])
            ys = _normalize(coords[:, 1])

            clusters = min(4, len(vector_assets))
            if clusters <= 1:
                labels = np.zeros(len(vector_assets), dtype=int)
            else:
                km = KMeans(n_clusters=clusters, random_state=42, n_init=10)
                labels = km.fit_predict(matrix)

            for idx, asset in enumerate(vector_assets):
                points[asset.id] = {
                    "x": float(np.clip(xs[idx], 0.0, 100.0)),
                    "y": float(np.clip(ys[idx], 0.0, 100.0)),
                    "cluster_id": int(labels[idx]),
                    "status": "ok",
                }
        except Exception:
            for asset in vector_assets:
                points[asset.id] = _fallback_point(asset)

        for asset in fallback_assets:
            points[asset.id] = _fallback_point(asset)

    result: list[dict] = []
    for asset in assets:
        point = points.get(asset.id, _fallback_point(asset))
        result.append(
            {
                "asset_id": asset.id,
                "filename": asset.original_filename,
                "preview_url": asset.preview_path or asset.stored_path,
                "x": float(np.clip(point["x"], 0.0, 100.0)),
                "y": float(np.clip(point["y"], 0.0, 100.0)),
                "cluster_id": point.get("cluster_id"),
                "width": asset.width,
                "height": asset.height,
                "file_size": asset.size_bytes,
                "aspect_ratio": asset.aspect_ratio,
                "status": point.get("status", "ok"),
            }
        )

    return result
