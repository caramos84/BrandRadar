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

## OCR and visual region extraction

For image assets (`jpg`, `jpeg`, `png`), upload processing now runs best-effort OCR and heuristic visual region detection before scoring:

- OCR uses `pytesseract` when available and gracefully falls back to OCR.space if local Tesseract is unavailable and `OCR_SPACE_API_KEY` is configured.
- Visual regions use simple OpenCV contour-based heuristics (grayscale, edges, contour bounding boxes, small-box filtering).
- Extracted text blocks and regions are persisted (`ocr_text`, `vision_data_json`) and feed `conversion_signal_score` and `visual_load_score`.

## OCR configuration

- `OCR_SPACE_API_KEY`: optional API key for OCR.space fallback if local Tesseract is unavailable.
- `OCR_SPACE_ENDPOINT`: endpoint URL, default `https://api.ocr.space/parse/image`.
- `OCR_PROVIDER`: optional provider selection, defaults to `auto`.

**Note:** OCR.space requests use temporary optimized images (max 1600x1600, JPEG quality 80) to avoid payload size limits. Original uploaded assets are never modified.

These signals are MVP structural heuristics to improve explainability and product behavior. They are not final ML predictions.

## OCR diagnostics and filename signal heuristics

- OCR is best-effort. If OCR is unavailable or fails, upload continues and assets expose diagnostics via `ocr_status` and `ocr_error`.
- `conversion_signal_score` uses OCR text when available and falls back to filename/metadata heuristics for retail naming conventions.
- Conversion Signal is a rule-based signal score for conversion-associated cues, not a prediction.
