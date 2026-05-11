import { Analysis } from '../api/analyses';

type Props = {
  analyses: Analysis[];
  loading: boolean;
  error: string;
  onCreate: () => void;
  onOpen: (analysisId: number) => void;
};

export function AnalysisListScreen({ analyses, loading, error, onCreate, onOpen }: Props) {
  return (
    <section className="content app-content">
      <h1 className="module-title">YOUR ANALYSIS</h1>
      {error && <p className="feedback feedback-error">{error}</p>}
      <div className="analysis-grid">
        <button className="analysis-card create-card" onClick={onCreate}>Create New Analysis</button>
        {analyses.map((analysis) => (
          <button key={analysis.id} className="analysis-card" onClick={() => onOpen(analysis.id)}>
            <strong>{analysis.brand_name}</strong>
            <span>{analysis.custom_category || analysis.category}</span>
            <span>{new Date(analysis.created_at).toLocaleDateString()}</span>
            <span>{analysis.asset_count} assets</span>
            <span className="status-pill">{analysis.status}</span>
          </button>
        ))}
      </div>
      {loading && <p className="status-message">Loading analyses...</p>}
      {!loading && analyses.length === 0 && (
        <p className="status-message">No analysis created yet. Start by creating your first brand analysis.</p>
      )}
    </section>
  );
}
