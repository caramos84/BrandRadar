import { useEffect, useMemo, useState } from 'react';

import { AnalysisDetail, AnalysisMapPoint, getAnalysisMap } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  token: string;
  onBack: () => void;
};

type ViewMode = 'mosaic' | 'list' | 'map';

type PlotPoint = {
  assetId: number;
  x: number;
  y: number;
};


const CHART_WIDTH = 1200;
const CHART_HEIGHT = 420;
const PLOT_PADDING_LEFT = 70;
const PLOT_PADDING_RIGHT = 40;
const PLOT_PADDING_TOP = 20;
const PLOT_PADDING_BOTTOM = 26;
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

const RADAR_AXES = [
  { key: 'visualLoad', label: 'Visual Load', field: 'visual_load_score' },
  { key: 'conversionIntent', label: 'Conversion Intent', field: 'conversion_signal_score' },
  { key: 'languageStress', label: 'Language Stress', field: 'text_density' },
  { key: 'layoutComplexity', label: 'Layout Complexity', field: 'layout_density' },
  { key: 'attentionDispersion', label: 'Attention Dispersion', field: 'region_count' },
  { key: 'brandSignalClarity', label: 'Brand Signal Clarity', field: 'logo_candidate_detected' },
] as const;

type RadarScoreKey = typeof RADAR_AXES[number]['key'];

type RadarScores = Record<RadarScoreKey, number>;

function clamp01(value: number | null | undefined) {
  return Math.min(1, Math.max(0, value ?? 0));
}

function radarPoint(center: number, radius: number, angle: number, score: number) {
  const safeScore = clamp01(score);
  return {
    x: center + Math.cos(angle) * radius * safeScore,
    y: center + Math.sin(angle) * radius * safeScore,
  };
}

function radarPolygon(points: Array<{ x: number; y: number }>) {
  return points.map((point) => `${point.x},${point.y}`).join(' ');
}

type HeatmapIntensity = 'Low' | 'Medium' | 'High';

function normalizeValue(value: number | null | undefined, max = 100) {
  return clamp01((value ?? 0) / max);
}

function getAttentionIntensity(asset: Record<string, any> | null): HeatmapIntensity {
  const visualLoad = normalizeValue(asset?.visual_load_score);
  const conversion = normalizeValue(asset?.conversion_signal_score);
  const regionCount = clamp01((asset?.region_count ?? 0) / 24);
  const score = clamp01(visualLoad * 0.45 + conversion * 0.45 + regionCount * 0.1);
  if (score < 0.33) return 'Low';
  if (score < 0.66) return 'Medium';
  return 'High';
}

function getFocusDispersion(asset: Record<string, any> | null): HeatmapIntensity {
  const regionCount = clamp01((asset?.region_count ?? 0) / 18);
  const textBlocks = clamp01((asset?.text_block_count ?? 0) / 16);
  const visualLoad = normalizeValue(asset?.visual_load_score);
  const score = clamp01(regionCount * 0.45 + textBlocks * 0.35 + (1 - visualLoad) * 0.2);
  if (score < 0.33) return 'Low';
  if (score < 0.66) return 'Medium';
  return 'High';
}

function getHeatmapVariant(asset: Record<string, any> | null) {
  const intensity = getAttentionIntensity(asset);
  const dispersion = getFocusDispersion(asset);
  if (intensity === 'High' && dispersion !== 'Low') return 'layout-c';
  if (dispersion === 'High') return 'layout-b';
  return 'layout-a';
}

function RadarChart({ scores }: { scores: RadarScores }) {
  const viewSize = 320;
  const center = viewSize / 2;
  const radius = 105;
  const angleStep = (2 * Math.PI) / RADAR_AXES.length;
  const gridLevels = [0.25, 0.5, 0.75, 1];

  const axisPoints = RADAR_AXES.map((axis, index) => {
    const angle = angleStep * index - Math.PI / 2;
    const value = clamp01(scores[axis.key]);
    return {
      ...radarPoint(center, radius, angle, value),
      angle,
      label: axis.label,
    };
  });

  return (
    <div className="drawer-radar-shell">
      <svg viewBox="0 0 320 320" className="drawer-radar-svg" aria-label="Radar score chart">
        {gridLevels.map((level) => {
          const gridPoints = RADAR_AXES.map((_, index) => {
            const angle = angleStep * index - Math.PI / 2;
            return radarPoint(center, radius * level, angle, 1);
          });
          return (
            <polygon
              key={`grid-${level}`}
              points={radarPolygon(gridPoints)}
              className="drawer-radar-grid-line"
            />
          );
        })}
        {RADAR_AXES.map((_, index) => {
          const angle = angleStep * index - Math.PI / 2;
          const endpoint = radarPoint(center, radius, angle, 1);
          return (
            <line
              key={`axis-${index}`}
              x1={center}
              y1={center}
              x2={endpoint.x}
              y2={endpoint.y}
              className="drawer-radar-axis-line"
            />
          );
        })}
        <polygon
          points={radarPolygon(axisPoints)}
          className="drawer-radar-score-area"
        />
        <polyline
          points={radarPolygon(axisPoints)}
          className="drawer-radar-score-line"
        />
        {axisPoints.map((point, index) => (
          <circle
            key={`point-${index}`}
            cx={point.x}
            cy={point.y}
            r={4}
            className="drawer-radar-score-point"
          />
        ))}
        {axisPoints.map((point, index) => {
          const labelOffset = 22;
          const angle = point.angle;
          const labelX = center + Math.cos(angle) * (radius + labelOffset);
          const labelY = center + Math.sin(angle) * (radius + labelOffset);
          const textAnchor = Math.abs(Math.cos(angle)) < 0.3 ? 'middle' : Math.cos(angle) > 0 ? 'start' : 'end';
          const dy = Math.sin(angle) > 0.4 ? '0.8em' : Math.sin(angle) < -0.4 ? '-0.2em' : '0.35em';
          return (
            <text
              key={`label-${index}`}
              x={labelX}
              y={labelY}
              dy={dy}
              textAnchor={textAnchor}
              className="drawer-radar-label"
            >
              {point.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

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
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<'heatmap' | 'stress' | 'radar' | 'layout'>('radar');
  const [mapPoints, setMapPoints] = useState<AnalysisMapPoint[]>([]);
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState('');

  const orderedAssets = useMemo(() => [...analysis.assets], [analysis.assets]);
  const selectedAsset = orderedAssets.find((asset) => asset.id === selectedAssetId) ?? null;

  const scoreLabel = (score: number | null) => (score != null ? formatScore(score) : 'MVP estimate pending');
  const isOcrUnavailable = selectedAsset ? !selectedAsset.ocr_status || selectedAsset.ocr_status === 'not_attempted' || selectedAsset.ocr_status === 'not_available' : false;

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

  const mapSummary = useMemo(() => {
    const conversionValues = mapPoints.map((point) => point.x).filter((value): value is number => value != null);
    const visualValues = mapPoints.map((point) => point.y).filter((value): value is number => value != null);
    const avgConversionIntent = average(conversionValues);
    const avgVisualLoad = average(visualValues);
    const dominantTerritory = (() => {
      if (avgConversionIntent == null || avgVisualLoad == null) return 'Unclassified';
      const intentHigh = avgConversionIntent >= 50;
      const loadHigh = avgVisualLoad >= 50;
      if (!intentHigh && !loadHigh) return 'Atmospheric Minimal';
      if (intentHigh && !loadHigh) return 'Precision Conversion';
      if (!intentHigh && loadHigh) return 'Narrative Density';
      return 'Hypercommerce';
    })();

    return {
      avgConversionIntent,
      avgVisualLoad,
      dominantTerritory,
    };
  }, [mapPoints]);

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
  const heatmapAsset = selectedAsset as Record<string, any> | null;
  const heatmapPreviewPath = selectedAsset?.preview_path || selectedMapPoint?.preview_url;
  const heatmapPreviewSrc = heatmapPreviewPath ? `${API_BASE_URL}${heatmapPreviewPath}` : null;
  const heatmapIntensity = useMemo(() => getAttentionIntensity(heatmapAsset), [heatmapAsset]);
  const focusDispersion = useMemo(() => getFocusDispersion(heatmapAsset), [heatmapAsset]);
  const heatmapLayout = useMemo(() => getHeatmapVariant(heatmapAsset), [heatmapAsset]);

  const radarScores = useMemo<RadarScores>(() => {
    const asset = selectedAsset as Record<string, any> | undefined;
    const visualLoad = clamp01((asset?.visual_load_score ?? 0) / 100);
    const conversionIntent = clamp01((asset?.conversion_signal_score ?? 0) / 100);
    const languageStress = clamp01((asset?.text_density ?? 0) / 100);
    const layoutComplexity = clamp01((asset?.layout_density ?? 0) / 100);
    const attentionDispersion = clamp01((((asset?.region_count ?? 0) / 24) + ((asset?.text_block_count ?? 0) / 20)) / 2);
    const brandSignalClarity = clamp01((asset?.logo_candidate_detected ? 0.8 : 0.35) + (asset?.cta_detected ? 0.1 : 0) - (asset?.promo_detected ? 0.05 : 0));
    return { visualLoad, conversionIntent, languageStress, layoutComplexity, attentionDispersion, brandSignalClarity };
  }, [selectedAsset]);

  const radarTerritory = useMemo(() => {
    const intentHigh = radarScores.conversionIntent >= 0.5;
    const loadHigh = radarScores.visualLoad >= 0.5;
    if (!intentHigh && !loadHigh) return 'Atmospheric Minimal';
    if (intentHigh && !loadHigh) return 'Precision Conversion';
    if (!intentHigh && loadHigh) return 'Narrative Density';
    return 'Hypercommerce';
  }, [radarScores]);

  const handleSelectAsset = (assetId: number) => {
    setSelectedAssetId(assetId);
    setActiveAnalysisTab('radar');
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
            <article key={asset.id} className="analysis-card asset-card-refined" onClick={() => handleSelectAsset(asset.id)}>
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
            <article key={asset.id} className="analysis-card asset-list-row" onClick={() => handleSelectAsset(asset.id)}>
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
              <div className="map-y-axis-label">Visual Load %</div>
              <svg className="asset-map asset-map-wide" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Asset map by conversion and visual load">
                <line x1={PLOT_PADDING_LEFT} y1={CHART_HEIGHT - PLOT_PADDING_BOTTOM} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-axis" />
                <line x1={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y1={PLOT_PADDING_TOP} x2={PLOT_PADDING_LEFT + PLOT_WIDTH / 2} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM} className="map-grid" />
                <line x1={PLOT_PADDING_LEFT} y1={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} x2={CHART_WIDTH - PLOT_PADDING_RIGHT} y2={PLOT_PADDING_TOP + PLOT_HEIGHT / 2} className="map-grid" />

                {[0, 25, 50, 75, 100].map((value) => {
                  const x = PLOT_PADDING_LEFT + (value / 100) * PLOT_WIDTH;
                  return (
                    <g key={`x-tick-${value}`}>
                      <line x1={x} y1={CHART_HEIGHT - PLOT_PADDING_BOTTOM} x2={x} y2={CHART_HEIGHT - PLOT_PADDING_BOTTOM + 6} className="map-axis-tick" />
                      <text x={x} y={CHART_HEIGHT - PLOT_PADDING_BOTTOM + 20} className="map-axis-tick-label" textAnchor="middle">{`${value}%`}</text>
                    </g>
                  );
                })}
                {[0, 25, 50, 75, 100].map((value) => {
                  const y = PLOT_PADDING_TOP + (1 - value / 100) * PLOT_HEIGHT;
                  return (
                    <g key={`y-tick-${value}`}>
                      <line x1={PLOT_PADDING_LEFT - 6} y1={y} x2={PLOT_PADDING_LEFT} y2={y} className="map-axis-tick" />
                      <text x={PLOT_PADDING_LEFT - 10} y={y + 4} className="map-axis-tick-label" textAnchor="end">{`${value}%`}</text>
                    </g>
                  );
                })}

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

            <p className="map-x-axis-label">Conversion Intent %</p>
            <p className="map-caption">Assets are positioned by conversion intent and visual load, with clusters representing visual behavior groups.</p>
            {mapLoading && <p className="map-status-message">Generating visual map...</p>}
            {!mapLoading && mapError && <p className="map-status-message">{mapError}</p>}
            {!mapLoading && !mapError && mapPoints.length === 0 && <p className="map-status-message">No visual map points available.</p>}
          </article>

          <article className="analysis-card diagnostic-panel diagnostic-panel-secondary">
            <h3 className="asset-name">Brand Summary</h3>
            <div className="map-summary-grid">
              <div>
                <span className="asset-meta-primary">Total assets</span>
                <p className="asset-meta-secondary"><strong>{orderedAssets.length}</strong></p>
              </div>
              <div>
                <span className="asset-meta-primary">Avg Visual Load</span>
                <p className="asset-meta-secondary"><strong>{mapSummary.avgVisualLoad != null ? formatScore(mapSummary.avgVisualLoad) : 'N/A'}</strong></p>
              </div>
              <div>
                <span className="asset-meta-primary">Avg Conversion Intent</span>
                <p className="asset-meta-secondary"><strong>{mapSummary.avgConversionIntent != null ? formatScore(mapSummary.avgConversionIntent) : 'N/A'}</strong></p>
              </div>
              <div>
                <span className="asset-meta-primary">Dominant territory</span>
                <p className="asset-meta-secondary"><strong>{mapSummary.dominantTerritory}</strong></p>
              </div>
            </div>
            <div className="diagnostic-grid">
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
        </div>
      )}

      {isDrawerOpen && (selectedAsset || selectedMapPoint) && (
        <aside className="map-drawer" aria-label="Selected asset details">
          <button className="drawer-close" type="button" onClick={closeDrawer} aria-label="Close drawer">×</button>
          <h3 className="asset-name">{selectedAsset?.original_filename || selectedMapPoint?.filename || 'Unknown asset'}</h3>
          <div className="drawer-preview-frame">
            {(selectedAsset?.preview_path || selectedMapPoint?.preview_url) ? (
              <img
                src={`${API_BASE_URL}${selectedAsset?.preview_path || selectedMapPoint?.preview_url}`}
                alt={selectedAsset?.original_filename || selectedMapPoint?.filename || 'Asset preview'}
                className="asset-drawer-preview"
              />
            ) : (
              <div className="drawer-preview placeholder">No preview</div>
            )}
          </div>
          <div className="drawer-action-grid">
            <button
              type="button"
              className={`drawer-analysis-button ${activeAnalysisTab === 'heatmap' ? 'active' : ''}`}
              onClick={() => setActiveAnalysisTab('heatmap')}
            >
              HEATMAP ANALYSIS
            </button>
            <button
              type="button"
              className={`drawer-analysis-button ${activeAnalysisTab === 'stress' ? 'active' : ''}`}
              onClick={() => setActiveAnalysisTab('stress')}
            >
              STRESS LANGUAGE
            </button>
            <button
              type="button"
              className={`drawer-analysis-button ${activeAnalysisTab === 'radar' ? 'active' : ''}`}
              onClick={() => setActiveAnalysisTab('radar')}
            >
              RADAR VIEW
            </button>
            <button
              type="button"
              className={`drawer-analysis-button ${activeAnalysisTab === 'layout' ? 'active' : ''}`}
              onClick={() => setActiveAnalysisTab('layout')}
            >
              LAYOUT
            </button>
          </div>
          <div className="drawer-analysis-content">
            {activeAnalysisTab === 'heatmap' && (
              <div className="drawer-analysis-block">
                <h4 className="drawer-panel-title">Heatmap Analysis</h4>
                <p className="asset-meta-secondary">Estimated attention map based on available visual signals.</p>
                <div className={`drawer-heatmap-frame heatmap-intensity-${heatmapIntensity.toLowerCase()} heatmap-dispersion-${focusDispersion.toLowerCase()} ${heatmapLayout}`}>
                  {heatmapPreviewSrc ? (
                    <img
                      src={heatmapPreviewSrc}
                      alt={selectedAsset?.original_filename || selectedMapPoint?.filename || 'Asset preview'}
                      className="drawer-heatmap-image"
                    />
                  ) : (
                    <div className="drawer-heatmap-placeholder">
                      <span>No image preview available</span>
                    </div>
                  )}
                  <div className="drawer-heatmap-overlay">
                    <div className="drawer-heatmap-spot spot-a" />
                    <div className="drawer-heatmap-spot spot-b" />
                    <div className="drawer-heatmap-spot spot-c" />
                    <div className="drawer-heatmap-spot spot-d" />
                  </div>
                </div>
                <div className="drawer-heatmap-grid">
                  <div>
                    <span className="drawer-analysis-label">Detected regions</span>
                    <strong>{selectedAsset?.region_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Visual load</span>
                    <strong>{selectedAsset?.visual_load_score != null ? formatScore(selectedAsset.visual_load_score) : 'N/A'}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Attention intensity</span>
                    <strong>{heatmapIntensity}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Focus dispersion</span>
                    <strong>{focusDispersion}</strong>
                  </div>
                </div>
                <div className="drawer-analysis-placeholder">
                  <span>{selectedAsset ? `This asset shows ${heatmapIntensity.toLowerCase()} attention intensity with ${focusDispersion.toLowerCase()} focus dispersion.` : 'This is an MVP estimate until the backend heatmap endpoint is connected.'}</span>
                  <small>MVP estimate. Real heatmap endpoint can be connected later.</small>
                </div>
              </div>
            )}
            {activeAnalysisTab === 'stress' && (
              <div className="drawer-analysis-block">
                <h4 className="drawer-panel-title">Stress Language</h4>
                <p className="asset-meta-secondary">
                  {isOcrUnavailable
                    ? 'OCR engine pending. Language stress is currently estimated from available metadata.'
                    : 'This panel surfaces OCR status and conversion signal stress.'}
                </p>
                <div className="drawer-analysis-grid">
                  <div>
                    <span className="drawer-analysis-label">OCR status</span>
                    <strong>{selectedAsset?.ocr_status ?? 'OCR unavailable'}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Text blocks</span>
                    <strong>{selectedAsset?.text_block_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Conversion signal</span>
                    <strong>{selectedAsset?.conversion_signal_score != null ? formatScore(selectedAsset.conversion_signal_score) : 'Pending OCR engine'}</strong>
                  </div>
                </div>
                <div className="drawer-analysis-placeholder">
                  <span>{isOcrUnavailable ? 'OCR unavailable' : 'Language stress estimate'}</span>
                  <small>{isOcrUnavailable ? 'Using metadata and fallback values while OCR is unavailable.' : 'Placeholder based on OCR and conversion signal.'}</small>
                </div>
              </div>
            )}
            {activeAnalysisTab === 'radar' && (
              <div className="drawer-analysis-block">
                <h4 className="drawer-panel-title">Radar View</h4>
                <p className="asset-meta-secondary">MVP visual behavior model based on available asset signals.</p>
                <div className="drawer-analysis-grid">
                  <div>
                    <span className="drawer-analysis-label">Visual Load</span>
                    <strong>{scoreLabel(selectedAsset?.visual_load_score ?? null)}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Conversion Signal</span>
                    <strong>{scoreLabel(selectedAsset?.conversion_signal_score ?? null)}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Cluster label</span>
                    <strong>{selectedAsset?.analysis_cluster_label || 'Unclassified'}</strong>
                  </div>
                </div>
                <RadarChart scores={radarScores} />
                <div className="drawer-radar-bars">
                  {RADAR_AXES.map((axis) => {
                    const score = radarScores[axis.key];
                    return (
                      <div key={axis.key} className="drawer-radar-row">
                        <span className="drawer-analysis-label">{axis.label}</span>
                        <div className="drawer-radar-bar">
                          <meter
                            className="drawer-radar-meter"
                            min={0}
                            max={100}
                            value={Math.round(score * 100)}
                          />
                        </div>
                        <strong className="drawer-radar-value">{Math.round(score * 100)}%</strong>
                      </div>
                    );
                  })}
                </div>
                <div className="drawer-analysis-placeholder">
                  <span>{selectedAsset ? radarTerritory : 'Radar view estimate'}</span>
                  <small>{selectedAsset ? 'Based on visual load and conversion intent plus derived asset metrics.' : 'Select an asset to view its radar profile.'}</small>
                </div>
              </div>
            )}
            {activeAnalysisTab === 'layout' && (
              <div className="drawer-analysis-block">
                <h4 className="drawer-panel-title">Layout</h4>
                <p className="asset-meta-secondary">Layout complexity is estimated from detected visual regions and text blocks.</p>
                <div className="drawer-analysis-grid">
                  <div>
                    <span className="drawer-analysis-label">Regions</span>
                    <strong>{selectedAsset?.region_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Text blocks</span>
                    <strong>{selectedAsset?.text_block_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="drawer-analysis-label">Complexity</span>
                    <strong>{(() => {
                      const regions = selectedAsset?.region_count ?? 0;
                      if (regions > 18) return 'High';
                      if (regions >= 8) return 'Medium';
                      return 'Low';
                    })()}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="drawer-meta-panel">
            <p className="asset-meta-primary">{selectedAsset ? `${selectedAsset.file_type.toUpperCase()} · ${selectedAsset.mime_type}` : 'MAP point metadata'}</p>
            <p className="asset-meta-secondary">{selectedAsset?.width && selectedAsset?.height ? `${selectedAsset.width} × ${selectedAsset.height}` : selectedMapPoint?.width && selectedMapPoint?.height ? `${selectedMapPoint.width} × ${selectedMapPoint.height}` : 'Dimensions unavailable'}</p>
            <p className="asset-meta-secondary">File size: {formatFileSize(selectedAsset?.size_bytes ?? selectedMapPoint?.file_size ?? 0)}</p>
            <p className="asset-meta-secondary">Map Cluster ID: {selectedMapPoint?.cluster_id ?? 0}</p>
            <p className="asset-meta-secondary">Map Status: {selectedMapPoint?.status ?? 'ok'}</p>
          </div>
          {selectedAsset && (
            <div className="drawer-analysis-panel">
              <h4 className="drawer-panel-title">Analysis Panel</h4>
              <p className="asset-meta-secondary">Cluster: {selectedAsset.analysis_cluster_label || 'Unclassified'}</p>
              <p className="asset-meta-secondary">Regions: {selectedAsset.region_count ?? 0}</p>
              <p className="asset-meta-secondary">Text blocks: {selectedAsset.text_block_count ?? 0}</p>
              <p className="asset-meta-secondary">OCR status: {selectedAsset.ocr_status || 'N/A'}</p>
              {selectedAsset.ocr_error && <p className="asset-meta-secondary">OCR error: {selectedAsset.ocr_error}</p>}
            </div>
          )}
        </aside>
      )}
    </section>
  );
}
