import { useMemo, useState } from 'react';

import { AnalysisDetail } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  onBack: () => void;
};

type ViewMode = 'mosaic' | 'list' | 'map';

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

const CLUSTERS = [
  'Brand / Lifestyle',
  'Product Hero',
  'Clean Conversion',
  'Promotional Heavy',
  'Informational Dense',
  'Unclassified',
] as const;

export function AnalysisDetailScreen({ analysis, onBack }: Props) {
  const [view, setView] = useState<ViewMode>('mosaic');
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [showExperimentalMap, setShowExperimentalMap] = useState(false);

  const orderedAssets = useMemo(() => [...analysis.assets], [analysis.assets]);
  const selectedAsset = orderedAssets.find((asset) => asset.id === selectedAssetId) ?? null;

  const diagnostics = useMemo(() => {
    const avgVisualLoad = average(orderedAssets.map((asset) => asset.visual_load_score));
    const avgConversion = average(orderedAssets.map((asset) => asset.conversion_signal_score));

    const ocrCompleted = orderedAssets.filter((asset) => asset.ocr_status === 'completed').length;
    const ocrUnavailableOrFailed = orderedAssets.filter((asset) => ['unavailable', 'failed'].includes(asset.ocr_status || '')).length;
    const ocrNotAvailable = orderedAssets.length - ocrCompleted - ocrUnavailableOrFailed;

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
      ocrUnavailableOrFailed,
      ocrNotAvailable,
      assetsWithTextBlocks,
      assetsWithRegions,
      clusterDistribution,
    };
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
              {asset.preview_path ? (
                <img src={`${API_BASE_URL}${asset.preview_path}`} alt={asset.original_filename} className="thumb" />
              ) : (
                <div className="thumb placeholder">PDF</div>
              )}
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
          <article className="analysis-card diagnostic-panel">
            <h3 className="asset-name">MAP Diagnostics</h3>
            <p className="map-caption">MAP view is currently using preliminary rule-based signals. OCR-based scoring is pending environment setup.</p>

            <div className="diagnostic-grid">
              <p>Total assets: <strong>{orderedAssets.length}</strong></p>
              <p>Avg Visual Load: <strong>{formatScore(diagnostics.avgVisualLoad)}</strong></p>
              <p>Avg Conversion Signal: <strong>{formatScore(diagnostics.avgConversion)}</strong></p>
              <p>OCR completed: <strong>{diagnostics.ocrCompleted}</strong></p>
              <p>OCR unavailable/failed: <strong>{diagnostics.ocrUnavailableOrFailed}</strong></p>
              <p>OCR N/A: <strong>{diagnostics.ocrNotAvailable}</strong></p>
              <p>Assets with text blocks: <strong>{diagnostics.assetsWithTextBlocks}</strong></p>
              <p>Assets with regions: <strong>{diagnostics.assetsWithRegions}</strong></p>
            </div>

            <div>
              <h4 className="asset-meta-primary">Cluster distribution</h4>
              <ul className="cluster-list-plain">
                {CLUSTERS.map((label) => (
                  <li key={label}>{label}: <strong>{diagnostics.clusterDistribution[label]}</strong></li>
                ))}
              </ul>
            </div>

            <button className="secondary-action" type="button" onClick={() => setShowExperimentalMap((prev) => !prev)}>
              {showExperimentalMap ? 'Hide Experimental MAP Plot' : 'Show Experimental MAP Plot'}
            </button>

            {showExperimentalMap && (
              <div className="experimental-map-shell">
                <svg className="asset-map" viewBox="0 0 100 100" role="img" aria-label="Experimental asset map">
                  <line x1="0" y1="100" x2="100" y2="100" className="map-axis" />
                  <line x1="0" y1="0" x2="0" y2="100" className="map-axis" />
                  {orderedAssets.map((asset) => {
                    const x = Math.max(0, Math.min(100, asset.conversion_signal_score ?? 0));
                    const y = 100 - Math.max(0, Math.min(100, asset.visual_load_score ?? 0));
                    return <circle key={asset.id} cx={x} cy={y} r={1.8} className="map-point" />;
                  })}
                </svg>
              </div>
            )}
          </article>

          <article className="analysis-card diagnostic-assets-list">
            <h3 className="asset-name">Asset Diagnostics</h3>
            <div className="diagnostic-table">
              {orderedAssets.map((asset) => (
                <button key={asset.id} className="diagnostic-row" onClick={() => handleSelectAsset(asset.id)}>
                  <span className="row-name">{asset.original_filename}</span>
                  <span>VL: {formatScore(asset.visual_load_score)}</span>
                  <span>CS: {formatScore(asset.conversion_signal_score)}</span>
                  <span>{asset.analysis_cluster_label || 'Unclassified'}</span>
                  <span>R: {asset.region_count ?? 0}</span>
                  <span>T: {asset.text_block_count ?? 0}</span>
                  <span>OCR: {asset.ocr_status || 'N/A'}</span>
                </button>
              ))}
            </div>
          </article>

          {isDrawerOpen && selectedAsset && (
            <aside className="map-drawer" aria-label="Selected asset details">
              <button className="drawer-close" type="button" onClick={closeDrawer} aria-label="Close drawer">×</button>
              <h3 className="asset-name">{selectedAsset.original_filename}</h3>

              {selectedAsset.preview_path ? (
                <img src={`${API_BASE_URL}${selectedAsset.preview_path}`} alt={selectedAsset.original_filename} className="thumb" />
              ) : (
                <div className="thumb placeholder">No preview</div>
              )}

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
