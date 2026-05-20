from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.assets import get_asset_attention, router


class DummyUser:
    id = 1


class DummyQuery:
    def __init__(self, result):
        self._result = result

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class DummyDb:
    def __init__(self, asset):
        self._asset = asset

    def query(self, *args, **kwargs):
        return DummyQuery(self._asset)


def test_attention_endpoint_shape(monkeypatch, tmp_path):
    class DummyAsset:
        id = 5
        analysis_id = 1
        preview_path = "/tmp/sample.jpg"
        stored_path = "/tmp/sample.jpg"
        text_block_count = 2
        region_count = 3

    app = FastAPI()
    app.include_router(router)

    import app.api.assets as assets_mod

    app.dependency_overrides[assets_mod.get_current_user] = lambda: DummyUser()
    app.dependency_overrides[assets_mod.get_db] = lambda: DummyDb(DummyAsset())
    monkeypatch.setattr(assets_mod, "run_attention_diagnostics", lambda *a, **k: {
        "heatmap_path": tmp_path / "heat.jpg",
        "primary_focus": {"x1": 1, "y1": 2, "x2": 20, "y2": 25, "strength": 0.9},
        "secondary_focus": [{"x1": 30, "y1": 40, "x2": 50, "y2": 60, "strength": 0.6}],
        "attention_dispersion": 0.4,
        "visual_noise": 0.3,
        "summary": "ok",
    })

    client = TestClient(app)
    res = client.get("/api/assets/5/attention")
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "asset_id",
        "heatmap_url",
        "primary_focus",
        "secondary_focus",
        "attention_dispersion",
        "visual_noise",
        "summary",
    }
