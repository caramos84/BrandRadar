from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from app.models.asset import Asset
from app.services.embedding_service import generate_visual_embedding


def _clamp_score(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return float(np.clip(numeric, 0.0, 100.0))


def _asset_signals(asset: Asset) -> dict:
    raw = getattr(asset, "vision_data_json", None)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    signals = parsed.get("asset_signals")
    return signals if isinstance(signals, dict) else {}


def _normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    lo = float(values.min())
    hi = float(values.max())
    if np.isclose(lo, hi):
        return np.full_like(values, 50.0, dtype=np.float32)
    return ((values - lo) / (hi - lo) * 100.0).astype(np.float32)


def _fallback_point(asset: Asset) -> dict:
    signals = _asset_signals(asset)
    x = _clamp_score(signals.get("conversion_intent"))
    if x is None:
        x = asset.conversion_signal_score
    if x is None:
        x = min(max((asset.aspect_ratio or 1.0) * 20.0, 0.0), 100.0)

    y = _clamp_score(signals.get("visual_load"))
    if y is None:
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
        signals = _asset_signals(asset)
        signal_x = _clamp_score(signals.get("conversion_intent"))
        signal_y = _clamp_score(signals.get("visual_load"))
        x = signal_x if signal_x is not None else point["x"]
        y = signal_y if signal_y is not None else point["y"]
        result.append(
            {
                "asset_id": asset.id,
                "filename": asset.original_filename,
                "preview_url": asset.preview_path or asset.stored_path,
                "x": float(np.clip(x, 0.0, 100.0)),
                "y": float(np.clip(y, 0.0, 100.0)),
                "cluster_id": point.get("cluster_id"),
                "width": asset.width,
                "height": asset.height,
                "file_size": asset.size_bytes,
                "aspect_ratio": asset.aspect_ratio,
                "status": point.get("status", "ok"),
            }
        )

    return result
