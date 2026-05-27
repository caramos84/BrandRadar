from types import SimpleNamespace

from app.services.clustering_service import generate_analysis_map_points


def _asset(asset_id: int, file_type: str = "jpg"):
    return SimpleNamespace(
        id=asset_id,
        original_filename=f"asset-{asset_id}.jpg",
        preview_path=f"/storage/uploads/{asset_id}.jpg",
        stored_path=f"/storage/uploads/{asset_id}.jpg",
        file_type=file_type,
        size_bytes=1000 + asset_id,
        width=100,
        height=100,
        aspect_ratio=1.0,
        conversion_signal_score=10.0 * asset_id,
        visual_load_score=5.0 * asset_id,
        embedding_json='[0.1,0.2,0.3,0.4]',
    )


def test_generate_analysis_map_points_shape_and_bounds():
    assets = [_asset(1), _asset(2), _asset(3)]

    points = generate_analysis_map_points(assets)

    assert len(points) == 3
    for point in points:
        assert set(point.keys()) >= {"asset_id", "filename", "x", "y", "cluster_id"}
        assert 0.0 <= point["x"] <= 100.0
        assert 0.0 <= point["y"] <= 100.0


def test_generate_analysis_map_points_fallback_for_single_asset():
    assets = [_asset(1)]
    points = generate_analysis_map_points(assets)

    assert len(points) == 1
    assert points[0]["cluster_id"] == 0
