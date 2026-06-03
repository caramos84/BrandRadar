# BrandRadar

BrandRadar is a full-stack brand asset analysis application. It lets users create a brand workspace, upload creative assets, and review a set of explainable visual, commercial, layout, attention, map, radar, and localization-fit diagnostics.

The project is currently structured as a FastAPI backend and a React + TypeScript + Vite frontend.

## What BrandRadar does

BrandRadar helps production and brand teams inspect uploaded creative assets through lightweight, explainable analysis layers:

- **Authentication and workspace access**: signup, login, current-user session restoration, and password recovery messaging.
- **Analysis workspaces**: create brand/category analyses and upload JPG, PNG, or PDF assets.
- **Asset metadata extraction**: dimensions, file size, type, preview path, and persisted asset records.
- **OCR and visual region extraction**: best-effort OCR plus heuristic region detection for image assets.
- **Attention heatmap**: backend-generated attention heatmap data and artifacts for asset inspection.
- **Asset signals**: stable `vision_data_json.asset_signals` metrics such as visual load, conversion intent, language stress, layout density, attention dispersion, brand signal clarity, promo presence, and commercial pressure.
- **Layout analysis**: structural block detection with classified blocks, summary text, and optional overlay/wireframe artifacts persisted in `vision_data_json.layout_analysis`.
- **Linguistic stress / Global Brand Guard**: deterministic multilingual expansion simulation for Spanish, Portuguese, German, French, Japanese, Korean, and Chinese persisted in `vision_data_json.linguistic_stress`.
- **Map and clustering**: analysis map points can prefer persisted asset signals for conversion and visual coordinates.
- **Frontend inspection UI**: list, map, heatmap, stress-language, radar, and layout views, plus toast alerts and a notification affordance.

## Repository layout

```text
BrandRadar/
├── backend/                  # FastAPI API, database models, analysis services, tests
│   ├── app/
│   │   ├── api/              # Auth, analyses, and asset endpoints
│   │   ├── core/             # Config and security helpers
│   │   ├── db/               # SQLAlchemy engine/session setup
│   │   ├── models/           # User, Analysis, Asset models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Vision, signals, layout, linguistic stress, clustering
│   ├── tests/                # Backend unit tests
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React + TypeScript + Vite app
│   ├── src/
│   │   ├── api/              # Frontend API clients
│   │   ├── screens/          # Main UI screens
│   │   ├── App.tsx           # App shell, auth routing, toasts/notifications
│   │   └── styles.css        # Global app styles
│   └── package.json          # Frontend scripts/dependencies
├── docs/                     # Product and scope notes
├── notebooks/                # Historical/prototyping notebooks
└── references/               # Reference assets/placeholders
```

## Backend overview

### Stack

- FastAPI
- SQLAlchemy
- SQLite by default
- Pydantic
- JWT auth via `python-jose`
- Password hashing via `passlib[bcrypt]`
- Pillow, OpenCV, pytesseract, NumPy, and scikit-learn for asset processing utilities

### Main backend responsibilities

- Serve the API and static uploaded files from `/storage`.
- Manage auth endpoints and bearer-token protected analysis routes.
- Persist users, analyses, and assets.
- Process uploaded image assets through OCR, visual feature extraction, heatmap generation, asset signals, layout analysis, and linguistic stress simulation.
- Store stable derived payloads inside `Asset.vision_data_json` without adding separate database columns for every analysis layer.

### Key backend files

- `backend/app/main.py` — FastAPI app setup, CORS, DB table creation, storage mount, routers.
- `backend/app/api/auth.py` — signup, login, current user, forgot password.
- `backend/app/api/analyses.py` — analysis CRUD/listing, asset upload, recompute/backfill, map responses.
- `backend/app/api/assets.py` — asset-specific endpoints.
- `backend/app/services/asset_vision.py` — image analysis orchestration and vision payload serialization.
- `backend/app/services/asset_signals.py` — normalized asset-level signal generation.
- `backend/app/services/layout_analysis.py` — structural layout block detection and artifacts.
- `backend/app/services/linguistic_stress.py` — offline multilingual copyfit risk simulation.
- `backend/app/services/clustering_service.py` — analysis map point generation.

## Frontend overview

### Stack

- React 18
- TypeScript
- Vite
- CSS in `frontend/src/styles.css`

### Main frontend responsibilities

- Auth screens for signup, login, and password recovery.
- Workspace shell with light/dark mode.
- Analysis list, create-analysis/upload flow, and analysis detail view.
- Map view and asset drawer.
- Heatmap, Stress Language, Radar, and Layout panels.
- Toast alerts for welcome, analysis success, and analysis failure states.
- Header notification bell that can replay the latest toast or show an empty state.

### Key frontend files

- `frontend/src/App.tsx` — app shell, auth/session transitions, analysis creation flow, toast and notification state.
- `frontend/src/api/auth.ts` — auth API client.
- `frontend/src/api/analyses.ts` — analysis, asset upload, and map API client.
- `frontend/src/screens/AnalysisListScreen.tsx` — analysis list and management UI.
- `frontend/src/screens/CreateAnalysisScreen.tsx` — brand/category form and upload dropzone.
- `frontend/src/screens/AnalysisDetailScreen.tsx` — map, drawer, heatmap, stress-language, radar, and layout views.
- `frontend/src/styles.css` — global styling, theme variants, map/drawer/chart styles, toasts, and notification indicator.

## Data flow

1. A user signs up or logs in through the frontend.
2. The frontend stores the JWT access token in `localStorage` and uses it for authenticated API calls.
3. The user creates an analysis with brand/category metadata.
4. The user uploads JPG, PNG, or PDF assets.
5. The backend stores files under `backend/storage/uploads` at runtime and creates `Asset` records.
6. For image assets, `analyze_image_asset()` computes OCR/vision payloads, heatmap data, layout analysis, and linguistic stress.
7. `attach_asset_signals()` adds stable `asset_signals` into the vision payload.
8. Feature fields and `vision_data_json` are persisted on the asset.
9. The frontend reloads analyses and renders list/map/detail views.
10. Analysis detail panels parse `vision_data_json` and use stored signals/analysis payloads for Radar, Layout, Stress Language, Heatmap, and Map-related UI.

## Persisted vision payloads

`vision_data_json` may include these important keys:

- `text_blocks`
- `visual_regions`
- `attention_grid`
- `attention_metrics`
- `heatmap_path` / heatmap-related fields
- `asset_signals`
- `layout_analysis`
- `linguistic_stress`
- OCR diagnostics such as `ocr_status` and `ocr_error`

The project intentionally keeps these analysis layers inside `vision_data_json` rather than creating many new database columns.

## Local development

### Prerequisites

- Python 3.11+ recommended
- Node.js and npm
- Optional: local Tesseract OCR binary if you want local OCR through `pytesseract`

### Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend defaults to SQLite at `sqlite:///./brandradar.db`.

### Frontend setup

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend API clients currently target:

```text
http://localhost:8000
```

### Open the app

- Frontend dev server: usually `http://localhost:5173`
- Backend health check: `http://localhost:8000/health`
- Uploaded/static files: served by the backend under `/storage`

## Environment variables

Backend settings are read in `backend/app/core/config.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `BrandRadar API` | Backend app name. |
| `DATABASE_URL` | `sqlite:///./brandradar.db` | SQLAlchemy database URL. |
| `JWT_SECRET_KEY` | `brandradar-mvp-secret-change-me` | JWT signing key. Change for real deployments. |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifetime. |
| `OCR_SPACE_API_KEY` | unset | Optional OCR.space fallback key. |
| `OCR_SPACE_ENDPOINT` | `https://api.ocr.space/parse/image` | OCR.space endpoint. |
| `OCR_PROVIDER` | `auto` | OCR provider selection. |

## API summary

### Health

- `GET /health`

### Auth

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`

### Analyses and assets

- `GET /api/analyses`
- `POST /api/analyses`
- `GET /api/analyses/{analysis_id}`
- `PATCH /api/analyses/{analysis_id}`
- `DELETE /api/analyses/{analysis_id}`
- `POST /api/analyses/{analysis_id}/assets`
- `GET /api/analyses/{analysis_id}/map`
- `POST /api/analyses/{analysis_id}/recompute-features`
- `GET /api/assets/{asset_id}/attention`

## Testing and validation

### Backend targeted tests

```bash
PYTHONPATH=backend pytest backend/tests/test_asset_signals.py
PYTHONPATH=backend pytest backend/tests/test_layout_analysis.py
PYTHONPATH=backend pytest backend/tests/test_linguistic_stress.py
PYTHONPATH=backend pytest backend/tests/test_clustering_service.py
```

### Backend full test suite

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

### Frontend build

```bash
npm --prefix frontend run build
```

If frontend dependencies are missing, install them first:

```bash
cd frontend
npm install
```

## Runtime storage and generated files

- Uploaded files are written under `backend/storage/uploads` at runtime.
- Layout overlay/wireframe artifacts may be generated next to uploaded images.
- Heatmap artifacts are backend-generated and should not be overwritten by layout artifacts.
- SQLite database files and uploaded storage are local runtime artifacts and should not be committed.

## Product notes

- Analysis scores are explainable heuristics intended for MVP product behavior, not predictive ML outputs.
- Linguistic Stress is an offline fit simulation. It does not call translation APIs and should not be described as actual translation.
- Heatmap, Radar, Map, Layout, Asset Signals, and Global Brand Guard are separate layers that share the same persisted vision payload.
- Current password recovery endpoint returns a safe message only; it does not send email.

## Troubleshooting

- **Frontend build cannot resolve React or JSX types**: run `npm install` in `frontend/` and then retry `npm run build`.
- **Backend import errors in tests**: activate the backend virtual environment and install `backend/requirements.txt`.
- **OCR unavailable**: ensure Tesseract is installed locally or configure OCR.space with `OCR_SPACE_API_KEY`. Upload continues with diagnostics if OCR fails.
- **No heatmap/layout artifacts**: verify the uploaded asset is an image and that the backend can write to `storage/uploads`.

## Current status

BrandRadar is an MVP-style application with a growing set of deterministic and heuristic brand asset diagnostics. Treat generated scores and classifications as decision-support signals for creative review, not final automated judgments.
