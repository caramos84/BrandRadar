import { useEffect, useMemo, useState } from 'react';

import { AnalysisDetail, AnalysisMapPoint, getAnalysisMap } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  token: string;
  onBack: () => void;
};

type ViewMode = 'mosaic' | 'list' | 'map';
type DrawerPanelMode = 'heatmap' | 'stress' | 'radar' | 'layout';

type PlotPoint = {
  assetId: number;
  x: number;
  y: number;
};

type RadarMetric = {
  label: string;
  value: number;
};


const CHART_WIDTH = 1200;
const CHART_HEIGHT = 500;
const PLOT_PADDING_LEFT = 70;
const PLOT_PADDING_RIGHT = 40;
const PLOT_PADDING_TOP = 35;
const PLOT_PADDING_BOTTOM = 55;
const PLOT_WIDTH = CHART_WIDTH - PLOT_PADDING_LEFT - PLOT_PADDING_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PLOT_PADDING_TOP - PLOT_PADDING_BOTTOM;
const POINT_INNER_PADDING_X = 32;

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
function clamp01(value: number) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function RadarChart({ scores }: { scores: RadarMetric[] }) {
  const safeScores = scores.map((item) => ({ ...item, value: clamp01(item.value) }));
  return (
    <div className="radar-chart-shell">
      <svg className="radar-chart-svg" viewBox="0 0 320 320" role="img" aria-label="Radar chart">
        {[0.25, 0.5, 0.75, 1].map((ring) => {
          const points = safeScores.map((_, index) => {
            const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeScores.length;
            const x = 160 + Math.cos(angle) * 105 * ring;
            const y = 160 + Math.sin(angle) * 105 * ring;
            return `${x},${y}`;
          }).join(' ');
          return <polygon key={ring} points={points} className="radar-grid-line" />;
        })}
        {safeScores.map((_, index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeScores.length;
          const x = 160 + Math.cos(angle) * 105;
          const y = 160 + Math.sin(angle) * 105;
          return <line key={`axis-${index}`} x1={160} y1={160} x2={x} y2={y} className="radar-axis-line" />;
        })}
        <polygon
          points={safeScores.map((item, index) => {
            const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeScores.length;
            const x = 160 + Math.cos(angle) * 105 * item.value;
            const y = 160 + Math.sin(angle) * 105 * item.value;
            return `${x},${y}`;
          }).join(' ')}
          className="radar-score-area"
        />
        <polyline
          points={safeScores.map((item, index) => {
            const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeScores.length;
            const x = 160 + Math.cos(angle) * 105 * item.value;
            const y = 160 + Math.sin(angle) * 105 * item.value;
            return `${x},${y}`;
          }).join(' ')}
          className="radar-score-line"
        />
        {safeScores.map((item, index) => {
          const angle = -Math.PI / 2 + (Math.PI * 2 * index) / safeScores.length;
          const x = 160 + Math.cos(angle) * 105 * item.value;
          const y = 160 + Math.sin(angle) * 105 * item.value;
          const lx = 160 + Math.cos(angle) * 123;
          const ly = 160 + Math.sin(angle) * 123;
          return (
            <g key={`pt-${item.label}`}>
              <circle cx={x} cy={y} r={3.2} className="radar-score-point" />
              <text x={lx} y={ly} textAnchor="middle" className="radar-chart-label">{item.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value != null);
  if (filtered.length === 0) return null;
  return filtered.reduce((sum, current) => sum + current, 0) / filtered.length;
}

function scoreToPlotX(score: number | null) {
  const safeScore = Math.max(0, Math.min(100, score ?? 0));
  return PLOT_PADDING_LEFT + POINT_INNER_PADDING_X + (safeScore / 100) * (PLOT_WIDTH - POINT_INNER_PADDING_X * 2);
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
      const isNearZeroConversion = point.x <= PLOT_PADDING_LEFT + POINT_INNER_PADDING_X + 1;
      const jitterX = spreadIndex * (isNearZeroConversion ? 14 : 10);
      const jitterY = ((point.assetId % 3) - 1) * (isNearZeroConversion ? 7 : 6);

      adjusted[point.assetId] = {
        x: Math.max(PLOT_PADDING_LEFT + POINT_INNER_PADDING_X, Math.min(CHART_WIDTH - PLOT_PADDING_RIGHT - POINT_INNER_PADDING_X, point.x + jitterX)),
        y: Math.max(PLOT_PADDING_TOP, Math.min(CHART_HEIGHT - PLOT_PADDING_BOTTOM, point.y + jitterY)),
      };
    });
  });

  return adjusted;
}

export function AnalysisDetailScreen({ analysis, token, onBack }: Props) {
  const [view, setView] = useState<ViewMode>('mosaic');
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeDrawerPanel, setActiveDrawerPanel] = useState<DrawerPanelMode>('radar');
  const [mapPoints, setMapPoints] = useState<AnalysisMapPoint[]>([]);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState('');

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

  useEffect(() => {
    if (view !== 'map') return;
    let cancelled = false;
    const loadMap = async () => {
      setMapLoading(true);
      setMapError('');
      try {
        const result = await getAnalysisMap(token, analysis.id);
        if (!cancelled) setMapPoints(result.points);
      } catch {
        if (!cancelled) setMapError('Visual map could not be loaded.');
      } finally {
        if (!cancelled) setMapLoading(false);
      }
    };
    void loadMap();
    return () => {
      cancelled = true;
    };
  }, [view, token, analysis.id]);

  const plotPositions = useMemo(() => {
    const basePoints = mapPoints.map((point) => ({
      assetId: point.asset_id,
      x: scoreToPlotX(point.x),
      y: scoreToPlotY(point.y),
    }));
    return applyDeterministicJitter(basePoints);
  }, [mapPoints]);

  const selectedMapPoint = mapPoints.find((point) => point.asset_id === selectedAssetId) ?? null;
  const effectiveRegionCount = selectedAsset?.region_count ?? 0;
  const effectiveTextBlockCount = selectedAsset?.text_block_count ?? 0;
  const effectiveVisualLoad = selectedAsset?.visual_load_score;
  const effectiveConversion = selectedAsset?.conversion_signal_score;
  const heatmapAttentionStatus = effectiveVisualLoad == null ? 'Medium' : effectiveVisualLoad > 66 ? 'High' : effectiveVisualLoad >= 33 ? 'Medium' : 'Low';
  const layoutComplexity = effectiveRegionCount > 18 ? 'High' : effectiveRegionCount >= 8 ? 'Medium' : 'Low';
  const radarScores = useMemo(() => {
    const visualLoad = clamp01((effectiveVisualLoad ?? 0) / 100);
    const conversionIntent = clamp01((effectiveConversion ?? 0) / 100);
    const languageStress = clamp01((effectiveTextBlockCount + (selectedAsset?.ocr_status === 'completed' ? 8 : 2)) / 30);
    const layoutScore = clamp01(effectiveRegionCount / 24);
    const attentionDispersion = clamp01((effectiveRegionCount * 0.65 + effectiveTextBlockCount * 0.35) / 25);
    const brandSignalClarity = clamp01(1 - (visualLoad * 0.45 + layoutScore * 0.35) + conversionIntent * 0.25);
    return [
      { label: 'Visual Load', value: visualLoad },
      { label: 'Conversion Intent', value: conversionIntent },
      { label: 'Language Stress', value: languageStress },
      { label: 'Layout Complexity', value: layoutScore },
      { label: 'Attention Dispersion', value: attentionDispersion },
      { label: 'Brand Clarity', value: brandSignalClarity },
    ];
  }, [effectiveConversion, effectiveRegionCount, effectiveTextBlockCount, effectiveVisualLoad, selectedAsset?.ocr_status]);

  const handleSelectAsset = (assetId: number) => {
    setSelectedAssetId(assetId);
    setActiveDrawerPanel('radar');
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
              <div className="map-y-axis-label">Visual Clustering Y</div>
              <svg className="asset-map asset-map-wide" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Asset map by conversion and visual load">
                <line x1={PLOT_PADDING_LEFT} y1={CHART_HEIGHT - PLOT_PADDING_BOTTOM} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-grid" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} className="map-grid" />

                {mapPoints.map((point) => {
                  const asset = orderedAssets.find((item) => item.id === point.asset_id) ?? null;
                  const plotted = plotPositions[point.asset_id] ?? { x: scoreToPlotX(point.x), y: scoreToPlotY(point.y) };
                  const isSelected = selectedAssetId === point.asset_id && isDrawerOpen;
                  const clusterClass = `map-point-cluster-${Math.abs(point.cluster_id ?? 0) % 4}`;

                  return (
                    <g key={point.asset_id} className="map-point-group" onClick={() => handleSelectAsset(point.asset_id)}>
                      <circle cx={plotted.x} cy={plotted.y} r={isSelected ? 6 : 4} className={`map-point ${clusterClass} ${isSelected ? 'map-point-selected' : ''}`} />
                      <title>
                        {point.filename}
                        {`\nX: ${formatScore(point.x)}`}
                        {`\nY: ${formatScore(point.y)}`}
                        {`\nCluster ID: ${point.cluster_id ?? 0}`}
                        {`\nStatus: ${point.status ?? 'ok'}`}
                        {asset ? `\nAsset: ${asset.original_filename}` : ''}
                      </title>
                    </g>
                  );
                })}
              </svg>
            </div>

            <p className="map-x-axis-label">Visual Clustering X</p>
            <p className="map-caption">Assets are positioned by visual similarity using backend-generated clustering coordinates.</p>
            {mapLoading && <p className="map-status-message">Generating visual map...</p>}
            {!mapLoading && mapError && <p className="map-status-message">{mapError}</p>}
            {!mapLoading && !mapError && mapPoints.length === 0 && <p className="map-status-message">No visual map points available.</p>}
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

          {isDrawerOpen && (selectedAsset || selectedMapPoint) && (
            <aside className="map-drawer" aria-label="Selected asset details">
              <button className="drawer-close" type="button" onClick={closeDrawer} aria-label="Close drawer">×</button>
              <h3 className="asset-name">{selectedAsset?.original_filename || selectedMapPoint?.filename || 'Unknown asset'}</h3>
              {(selectedAsset?.preview_path || selectedMapPoint?.preview_url) ? <img src={`${API_BASE_URL}${selectedAsset?.preview_path || selectedMapPoint?.preview_url}`} alt={selectedAsset?.original_filename || selectedMapPoint?.filename || 'Asset preview'} className="thumb" /> : <div className="thumb placeholder">No preview</div>}
              <div className="drawer-action-grid">
                <button type="button" className={`drawer-analysis-button ${activeDrawerPanel === 'heatmap' ? 'active' : ''}`} onClick={() => setActiveDrawerPanel('heatmap')}>HEATMAP ANALYSIS</button>
                <button type="button" className={`drawer-analysis-button ${activeDrawerPanel === 'stress' ? 'active' : ''}`} onClick={() => setActiveDrawerPanel('stress')}>STRESS LANGUAGE</button>
                <button type="button" className={`drawer-analysis-button ${activeDrawerPanel === 'radar' ? 'active' : ''}`} onClick={() => setActiveDrawerPanel('radar')}>RADAR VIEW</button>
                <button type="button" className={`drawer-analysis-button ${activeDrawerPanel === 'layout' ? 'active' : ''}`} onClick={() => setActiveDrawerPanel('layout')}>LAYOUT</button>
              </div>
              <div className="drawer-meta-panel">
                <p className="asset-meta-primary">{selectedAsset ? `${selectedAsset.file_type.toUpperCase()} · ${selectedAsset.mime_type}` : 'MAP point metadata'}</p>
                <p className="asset-meta-secondary">{selectedAsset?.width && selectedAsset?.height ? `${selectedAsset.width} × ${selectedAsset.height}` : selectedMapPoint?.width && selectedMapPoint?.height ? `${selectedMapPoint.width} × ${selectedMapPoint.height}` : 'Dimensions unavailable'}</p>
                <p className="asset-meta-secondary">File size: {formatFileSize(selectedAsset?.size_bytes ?? selectedMapPoint?.file_size ?? 0)}</p>
                <p className="asset-meta-secondary">Map Cluster ID: {selectedMapPoint?.cluster_id ?? 0}</p>
                <p className="asset-meta-secondary">Map Status: {selectedMapPoint?.status ?? 'ok'}</p>
              </div>
              <div className="drawer-analysis-panel">
                {activeDrawerPanel === 'radar' && (
                  <>
                    <h4 className="drawer-panel-title">Radar View</h4>
                    <p className="asset-meta-secondary">MVP visual behavior model based on available asset signals.</p>
                    <RadarChart scores={radarScores} />
                    <div className="radar-bars">
                      {radarScores.map((item) => (
                        <div key={item.label} className="radar-bar-row">
                          <span>{item.label}</span>
                          <div className="radar-bar-track"><div className="radar-bar-fill" style={{ width: `${Math.round(clamp01(item.value) * 100)}%` }} /></div>
                          <strong>{Math.round(clamp01(item.value) * 100)}%</strong>
                        </div>
                      ))}
                    </div>
                    <p className="asset-meta-secondary">Macroterritory reading: {selectedAsset?.analysis_cluster_label || 'Unclassified'}</p>
                    <p className="asset-meta-secondary">OCR note: {selectedAsset?.ocr_status === 'completed' ? 'OCR metadata available.' : 'OCR engine pending. Language dimensions are estimated.'}</p>
                  </>
                )}
                {activeDrawerPanel === 'heatmap' && (
                  <>
                    <h4 className="drawer-panel-title">Heatmap Analysis</h4>
                    <p className="asset-meta-secondary">Estimated attention based on detected regions and visual load.</p>
                    <p className="asset-meta-secondary">Detected regions: {effectiveRegionCount}</p>
                    <p className="asset-meta-secondary">Visual load: {effectiveVisualLoad == null ? 'MVP estimate pending' : formatScore(effectiveVisualLoad)}</p>
                    <p className="asset-meta-secondary">Attention status: {heatmapAttentionStatus}</p>
                  </>
                )}
                {activeDrawerPanel === 'stress' && (
                  <>
                    <h4 className="drawer-panel-title">Stress Language</h4>
                    <p className="asset-meta-secondary">OCR status: {selectedAsset?.ocr_status || 'N/A'}</p>
                    <p className="asset-meta-secondary">Text blocks: {effectiveTextBlockCount}</p>
                    <p className="asset-meta-secondary">Conversion intent score: {effectiveConversion == null ? 'MVP estimate pending' : formatScore(effectiveConversion)}</p>
                    {(!selectedAsset?.ocr_status || selectedAsset.ocr_status === 'N/A' || selectedAsset.ocr_status === 'not_attempted') && (
                      <p className="asset-meta-secondary">OCR engine pending. Language stress is currently estimated from available metadata.</p>
                    )}
                    {selectedAsset?.ocr_error && <p className="asset-meta-secondary">OCR error: {selectedAsset.ocr_error}</p>}
                  </>
                )}
                {activeDrawerPanel === 'layout' && (
                  <>
                    <h4 className="drawer-panel-title">Layout</h4>
                    <p className="asset-meta-secondary">Regions: {effectiveRegionCount}</p>
                    <p className="asset-meta-secondary">Text blocks: {effectiveTextBlockCount}</p>
                    <p className="asset-meta-secondary">Estimated layout complexity: {layoutComplexity}</p>
                    <p className="asset-meta-secondary">Layout complexity is estimated from detected visual regions and text blocks.</p>
                  </>
                )}
              </div>
            </aside>
          )}
        </div>
      )}
    </section>
  );
}
