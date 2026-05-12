import { useMemo, useState } from 'react';

import { AnalysisDetail } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  onBack: () => void;
};

type ViewMode = 'mosaic' | 'list' | 'map';

const CLUSTER_LABELS = [
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

export function AnalysisDetailScreen({ analysis, onBack }: Props) {
  const [view, setView] = useState<ViewMode>('mosaic');
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(analysis.assets[0]?.id ?? null);

  const orderedAssets = useMemo(() => [...analysis.assets], [analysis.assets]);
  const selectedAsset = orderedAssets.find((asset) => asset.id === selectedAssetId) ?? orderedAssets[0] ?? null;
  const allScoresMissing = orderedAssets.every(
    (asset) => asset.visual_load_score == null && asset.conversion_signal_score == null,
  );

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
        <div className="map-layout">
          <div className="map-panel analysis-card">
            <svg className="asset-map" viewBox="0 0 100 100" role="img" aria-label="Asset map by conversion and visual load">
              <line x1="0" y1="100" x2="100" y2="100" className="map-axis" />
              <line x1="0" y1="0" x2="0" y2="100" className="map-axis" />
              <line x1="50" y1="0" x2="50" y2="100" className="map-grid" />
              <line x1="0" y1="50" x2="100" y2="50" className="map-grid" />

              {orderedAssets.map((asset) => {
                const x = Math.max(0, Math.min(100, asset.conversion_signal_score ?? 0));
                const y = 100 - Math.max(0, Math.min(100, asset.visual_load_score ?? 0));
                const hasMissingScores = asset.conversion_signal_score == null || asset.visual_load_score == null;

                return (
                  <g key={asset.id} className="map-point-group" onClick={() => setSelectedAssetId(asset.id)}>
                    <circle
                      cx={x}
                      cy={y}
                      r={selectedAssetId === asset.id ? 2.5 : 1.8}
                      className={`map-point cluster-${(asset.analysis_cluster_label || 'Unclassified').replace(/[^a-zA-Z0-9]+/g, '-').toLowerCase()} ${hasMissingScores ? 'map-point-missing' : ''}`}
                    />
                    <title>
                      {asset.original_filename}
                      {`\nConversion: ${formatScore(asset.conversion_signal_score)}`}
                      {`\nVisual Load: ${formatScore(asset.visual_load_score)}`}
                      {`\nCluster: ${asset.analysis_cluster_label || 'Unclassified'}`}
                      {`\nDimensions: ${asset.width && asset.height ? `${asset.width}x${asset.height}` : 'N/A'}`}
                      {`\nSize: ${formatFileSize(asset.size_bytes)}`}
                      {hasMissingScores ? '\nScores unavailable' : ''}
                    </title>
                  </g>
                );
              })}
            </svg>

            <div className="map-axis-labels">
              <p>Low Conversion Signal → High Conversion Signal</p>
              <p className="map-y-label">Low Visual Load → High Visual Load</p>
            </div>
            <p className="map-caption">Assets are positioned by rule-based structural and conversion signals.</p>
            {allScoresMissing && <p className="feedback feedback-error">MAP requires analytical scores. Try recomputing features.</p>}

            <div className="map-legend">
              {CLUSTER_LABELS.map((label) => (
                <span key={label} className={`legend-item cluster-${label.replace(/[^a-zA-Z0-9]+/g, '-').toLowerCase()}`}>{label}</span>
              ))}
            </div>
          </div>

          <div className="analysis-card map-selected-panel">
            {selectedAsset ? (
              <>
                <h3 className="asset-name">{selectedAsset.original_filename}</h3>
                {selectedAsset.preview_path ? (
                  <img src={`${API_BASE_URL}${selectedAsset.preview_path}`} alt={selectedAsset.original_filename} className="thumb" />
                ) : (
                  <div className="thumb placeholder">No preview</div>
                )}
                <p className="asset-meta-primary">{selectedAsset.file_type.toUpperCase()} · {formatFileSize(selectedAsset.size_bytes)}</p>
                <p className="asset-meta-secondary">{selectedAsset.width && selectedAsset.height ? `${selectedAsset.width} × ${selectedAsset.height}` : 'Dimensions unavailable'}</p>
                <p className="asset-meta-secondary">Conversion Signal: {formatScore(selectedAsset.conversion_signal_score)}</p>
                <p className="asset-meta-secondary">Visual Load: {formatScore(selectedAsset.visual_load_score)}</p>
                <p className="asset-meta-secondary">Cluster: {selectedAsset.analysis_cluster_label || 'Unclassified'}</p>
                <p className="asset-meta-secondary">Regions: {selectedAsset.region_count ?? 0}</p>
                <p className="asset-meta-secondary">Text blocks: {selectedAsset.text_block_count ?? 0}</p>
                <p className="asset-meta-secondary">OCR status: {selectedAsset.ocr_status || 'N/A'}</p>
                {(selectedAsset.conversion_signal_score == null || selectedAsset.visual_load_score == null) && (
                  <p className="feedback feedback-error">Scores unavailable</p>
                )}
              </>
            ) : (
              <p className="status-message">Select a point to inspect an asset.</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
