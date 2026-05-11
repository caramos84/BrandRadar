import { AnalysisDetail } from '../api/analyses';

const API_BASE_URL = 'http://localhost:8000';

type Props = {
  analysis: AnalysisDetail;
  onBack: () => void;
};

export function AnalysisDetailScreen({ analysis, onBack }: Props) {
  return (
    <section className="content app-content">
      <h1 className="module-title">{analysis.brand_name}</h1>
      <p>
        {analysis.custom_category || analysis.category} · {analysis.status} · {analysis.asset_count} assets · {new Date(analysis.created_at).toLocaleDateString()}
      </p>
      <div className="asset-grid">
        {analysis.assets.map((asset) => (
          <article key={asset.id} className="analysis-card">
            {asset.preview_path ? (
              <img src={`${API_BASE_URL}${asset.preview_path}`} alt={asset.original_filename} className="thumb" />
            ) : (
              <div className="thumb placeholder">PDF</div>
            )}
            <strong>{asset.original_filename}</strong>
            <span>{asset.file_type.toUpperCase()} · {asset.size_bytes} bytes</span>
            <span>{asset.width && asset.height ? `${asset.width}x${asset.height}` : 'N/A'}</span>
          </article>
        ))}
      </div>
      <button className="secondary-action" onClick={onBack}>Back to analyses</button>
    </section>
  );
}
