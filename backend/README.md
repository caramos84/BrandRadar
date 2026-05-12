# BrandRadar Backend (MVP Auth Foundation)

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`

## Asset analytical features

Each uploaded asset now stores MVP analytical feature fields.

- **Conversion Signal** (`conversion_signal_score`): rule-based score from `0` to `100` based on detected purchase/conversion-related signals in filename/text-like hints.
- **Visual Load** (`visual_load_score`): rule-based score from `0` to `100` using structural metadata (dimensions, pixel area, file size) and density proxies.

These are explainable, non-ML MVP features intended as groundwork for future analysis experiences (MAP, clustering, inspection panels). They are **not** predictive machine learning outputs.
