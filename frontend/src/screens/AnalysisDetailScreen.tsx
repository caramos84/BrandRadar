import { useMemo, useState } from 'react';

import { AnalysisDetail } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  onBack: () => void;
};

type ViewMode = 'mosaic' | 'list' | 'map';

type PlotPoint = {
  assetId: number;
  x: number;
  y: number;
};


const CHART_WIDTH = 1200;
const CHART_HEIGHT = 500;
const PLOT_PADDING_LEFT = 70;
const PLOT_PADDING_RIGHT = 40;
const PLOT_PADDING_TOP = 35;
const PLOT_PADDING_BOTTOM = 55;
const PLOT_WIDTH = CHART_WIDTH - PLOT_PADDING_LEFT - PLOT_PADDING_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PLOT_PADDING_TOP - PLOT_PADDING_BOTTOM;

const CLUSTERS = [
  'Brand / Lifestyle',
  'Product Hero',
  'Clean Conversion',
  'Promotional Heavy',
  'Informational Dense',
  'Unclassified',
] as const;

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`;
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatScore(score: number | null) {
  return score == null ? 'N/A' : score.toFixed(1);
}

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value != null);
  if (filtered.length === 0) return null;
  return filtered.reduce((sum, current) => sum + current, 0) / filtered.length;
}

function scoreToPlotX(score: number | null) {
  const safeScore = Math.max(0, Math.min(100, score ?? 0));
  return PLOT_PADDING_LEFT + (safeScore / 100) * PLOT_WIDTH;
}

function scoreToPlotY(score: number | null) {
  const safeScore = Math.max(0, Math.min(100, score ?? 0));
  return PLOT_PADDING_TOP + (1 - safeScore / 100) * PLOT_HEIGHT;
}

function applyDeterministicJitter(points: PlotPoint[]): Record<number, { x: number; y: number }> {
  const grouped = new Map<string, PlotPoint[]>();

  points.forEach((point) => {
    const key = `${Math.round(point.x)}-${Math.round(point.y)}`;
    const bucket = grouped.get(key) ?? [];
    bucket.push(point);
    grouped.set(key, bucket);
  });

  const adjusted: Record<number, { x: number; y: number }> = {};

  grouped.forEach((bucket) => {
    const sorted = [...bucket].sort((a, b) => a.assetId - b.assetId);
    const count = sorted.length;
    const center = (count - 1) / 2;

    sorted.forEach((point, index) => {
      const spreadIndex = index - center;
      const jitterX = spreadIndex * 10;
      const jitterY = ((point.assetId % 3) - 1) * 6;

      adjusted[point.assetId] = {
        x: Math.max(PLOT_PADDING_LEFT, Math.min(CHART_WIDTH - PLOT_PADDING_RIGHT, point.x + jitterX)),
        y: Math.max(PLOT_PADDING_TOP, Math.min(CHART_HEIGHT - PLOT_PADDING_BOTTOM, point.y + jitterY)),
      };
    });
  });

  return adjusted;
}

export function AnalysisDetailScreen({ analysis, onBack }: Props) {
  const [view, setView] = useState<ViewMode>('mosaic');
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const orderedAssets = useMemo(() => [...analysis.assets], [analysis.assets]);
  const selectedAsset = orderedAssets.find((asset) => asset.id === selectedAssetId) ?? null;

  const diagnostics = useMemo(() => {
    const avgVisualLoad = average(orderedAssets.map((asset) => asset.visual_load_score));
    const avgConversion = average(orderedAssets.map((asset) => asset.conversion_signal_score));
    const ocrCompleted = orderedAssets.filter((asset) => asset.ocr_status === 'completed').length;
    const ocrNotAvailable = orderedAssets.length - ocrCompleted;
    const assetsWithTextBlocks = orderedAssets.filter((asset) => (asset.text_block_count ?? 0) > 0).length;
    const assetsWithRegions = orderedAssets.filter((asset) => (asset.region_count ?? 0) > 0).length;

    const clusterDistribution = CLUSTERS.reduce<Record<string, number>>((acc, label) => {
      acc[label] = orderedAssets.filter((asset) => (asset.analysis_cluster_label || 'Unclassified') === label).length;
      return acc;
    }, {});

    return {
      avgVisualLoad,
      avgConversion,
      ocrCompleted,
      ocrNotAvailable,
      assetsWithTextBlocks,
      assetsWithRegions,
      clusterDistribution,
    };
  }, [orderedAssets]);

  const plotPositions = useMemo(() => {
    const basePoints = orderedAssets.map((asset) => ({
      assetId: asset.id,
      x: scoreToPlotX(asset.conversion_signal_score),
      y: scoreToPlotY(asset.visual_load_score),
    }));
    return applyDeterministicJitter(basePoints);
  }, [orderedAssets]);

  const handleSelectAsset = (assetId: number) => {
    setSelectedAssetId(assetId);
    setIsDrawerOpen(true);
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedAssetId(null);
  };

  return (
    <section className="content app-content">
      <h1 className="module-title">{analysis.brand_name}</h1>
      <p>
        {analysis.custom_category || analysis.category} · {analysis.status} · {analysis.asset_count} assets · {new Date(analysis.created_at).toLocaleDateString()}
      </p>

      <div className="detail-controls">
        <button className="secondary-action control-back" onClick={onBack}>Back to Analysis</button>
        <button className={`view-control ${view === 'mosaic' ? 'active' : ''}`} onClick={() => setView('mosaic')}>MOSAIC</button>
        <button className={`view-control ${view === 'list' ? 'active' : ''}`} onClick={() => setView('list')}>LIST</button>
        <button className={`view-control ${view === 'map' ? 'active' : ''}`} onClick={() => setView('map')}>MAP</button>
      </div>

      {view === 'mosaic' && (
        <div className="asset-grid">
          {orderedAssets.map((asset) => (
            <article key={asset.id} className="analysis-card asset-card-refined">
              {asset.preview_path ? <img src={`${API_BASE_URL}${asset.preview_path}`} alt={asset.original_filename} className="thumb" /> : <div className="thumb placeholder">PDF</div>}
              <strong className="asset-name">{asset.original_filename}</strong>
              <span className="asset-meta-primary">{asset.file_type.toUpperCase()} · {formatFileSize(asset.size_bytes)}</span>
              <span className="asset-meta-secondary">{asset.width && asset.height ? `${asset.width} × ${asset.height}` : 'Dimensions unavailable'}</span>
            </article>
          ))}
        </div>
      )}

      {view === 'list' && (
        <div className="asset-list">
          {orderedAssets.map((asset) => (
            <article key={asset.id} className="analysis-card asset-list-row">
              <strong className="asset-name">{asset.original_filename}</strong>
              <span className="asset-meta-primary">{asset.file_type.toUpperCase()} · {formatFileSize(asset.size_bytes)}</span>
              <span className="asset-meta-secondary">{asset.width && asset.height ? `${asset.width} × ${asset.height}` : 'Dimensions unavailable'}</span>
            </article>
          ))}
        </div>
      )}

      {view === 'map' && (
        <div className="map-diagnostic-layout">
          <article className="analysis-card map-shell map-primary-shell">
            <div className="map-frame">
              <div className="map-y-axis-label">Low Visual Load → High Visual Load</div>
              <svg className="asset-map asset-map-wide" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Asset map by conversion and visual load">
                <line x1={PLOT_PADDING_LEFT} y1={CHART_HEIGHT - PLOT_PADDING_BOTTOM} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-grid" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} className="map-grid" />

                {orderedAssets.map((asset) => {
                  const plotted = plotPositions[asset.id] ?? { x: scoreToPlotX(asset.conversion_signal_score), y: scoreToPlotY(asset.visual_load_score) };
                  const hasMissingScores = asset.conversion_signal_score == null || asset.visual_load_score == null;
                  const isSelected = selectedAssetId === asset.id && isDrawerOpen;

                  return (
                    <g key={asset.id} className="map-point-group" onClick={() => handleSelectAsset(asset.id)}>
                      <circle cx={plotted.x} cy={plotted.y} r={isSelected ? 6 : 4} className={`map-point ${hasMissingScores ? 'map-point-missing' : ''} ${isSelected ? 'map-point-selected' : ''}`} />
                      <title>
                        {asset.original_filename}
                        {`\nConversion: ${formatScore(asset.conversion_signal_score)}`}
                        {`\nVisual Load: ${formatScore(asset.visual_load_score)}`}
                        {`\nCluster: ${asset.analysis_cluster_label || 'Unclassified'}`}
                      </title>
                    </g>
                  );
                })}
              </svg>
            </div>

            <p className="map-x-axis-label">Low Conversion Signal → High Conversion Signal</p>
            <p className="map-caption">Assets are positioned by rule-based structural and conversion signals. OCR scoring is pending environment setup.</p>
          </article>

          <article className="analysis-card diagnostic-panel diagnostic-panel-secondary">
            <h3 className="asset-name">MAP Diagnostics</h3>
            <div className="diagnostic-grid">
              <p>Total assets: <strong>{orderedAssets.length}</strong></p>
              <p>Avg Visual Load: <strong>{formatScore(diagnostics.avgVisualLoad)}</strong></p>
              <p>Avg Conversion Signal: <strong>{formatScore(diagnostics.avgConversion)}</strong></p>
              <p>OCR completed: <strong>{diagnostics.ocrCompleted}</strong></p>
              <p>OCR N/A: <strong>{diagnostics.ocrNotAvailable}</strong></p>
              <p>Assets with text blocks: <strong>{diagnostics.assetsWithTextBlocks}</strong></p>
              <p>Assets with regions: <strong>{diagnostics.assetsWithRegions}</strong></p>
            </div>
            <div>
              <h4 className="asset-meta-primary">Cluster distribution</h4>
              <ul className="cluster-list-plain">
                {CLUSTERS.map((label) => <li key={label}>{label}: <strong>{diagnostics.clusterDistribution[label]}</strong></li>)}
              </ul>
            </div>
          </article>

          {isDrawerOpen && selectedAsset && (
            <aside className="map-drawer" aria-label="Selected asset details">
              <button className="drawer-close" type="button" onClick={closeDrawer} aria-label="Close drawer">×</button>
              <h3 className="asset-name">{selectedAsset.original_filename}</h3>
              {selectedAsset.preview_path ? <img src={`${API_BASE_URL}${selectedAsset.preview_path}`} alt={selectedAsset.original_filename} className="thumb" /> : <div className="thumb placeholder">No preview</div>}
              <p className="asset-meta-primary">{selectedAsset.file_type.toUpperCase()} · {selectedAsset.mime_type}</p>
              <p className="asset-meta-secondary">{selectedAsset.width && selectedAsset.height ? `${selectedAsset.width} × ${selectedAsset.height}` : 'Dimensions unavailable'}</p>
              <p className="asset-meta-secondary">File size: {formatFileSize(selectedAsset.size_bytes)}</p>
              <p className="asset-meta-secondary">Conversion Signal: {formatScore(selectedAsset.conversion_signal_score)}</p>
              <p className="asset-meta-secondary">Visual Load: {formatScore(selectedAsset.visual_load_score)}</p>
              <p className="asset-meta-secondary">Cluster: {selectedAsset.analysis_cluster_label || 'Unclassified'}</p>
              <p className="asset-meta-secondary">Regions: {selectedAsset.region_count ?? 0}</p>
              <p className="asset-meta-secondary">Text blocks: {selectedAsset.text_block_count ?? 0}</p>
              <p className="asset-meta-secondary">OCR status: {selectedAsset.ocr_status || 'N/A'}</p>
              {selectedAsset.ocr_error && <p className="asset-meta-secondary">OCR error: {selectedAsset.ocr_error}</p>}
            </aside>
          )}
        </div>
      )}
    </section>
  );
}
