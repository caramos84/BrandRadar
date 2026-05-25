import { Analysis } from '../api/analyses';

type Props = {
  analyses: Analysis[];
  loading: boolean;
  error: string;
  onCreate: () => void;
  onOpen: (analysisId: number) => void;
};

const CATEGORY_EMOJI: Record<string, string> = {
  Retail: '🛒',
  'Drinks & Spirits': '🍸',
  Food: '🍽️',
  'Fashion / Wear': '👕',
  Vehicles: '🚗',
  Pharma: '💊',
  Convenience: '🏪',
  'Electronics / Mobile': '📱',
  Toys: '🧸',
  Office: '🗂️',
  Furniture: '🪑',
  'Bank / Fintech': '🏦',
  'Real Estate': '🏢',
  'Software / Devs': '💻',
  Entertainment: '🎬',
  Services: '🛠️',
  Transport: '🚚',
  Communications: '📡',
  Industry: '🏭',
  Pets: '🐾',
  Other: '✨',
};

function getCategoryEmoji(category: string) {
  return CATEGORY_EMOJI[category] ?? '✨';
}

export function AnalysisListScreen({ analyses, loading, error, onCreate, onOpen }: Props) {
  return (
    <section className="content app-content">
      <h1 className="module-title">YOUR ANALYSIS</h1>
      {error && <p className="feedback feedback-error">{error}</p>}

      <div className="analysis-grid refined-grid">
        <button className="analysis-card create-card create-card-strong" onClick={onCreate}>
          <span className="create-card-plus">＋</span>
          <span>Create New Analysis</span>
        </button>

        {analyses.map((analysis) => {
          const categoryLabel = analysis.custom_category || analysis.category;
          const emojiCategory = analysis.custom_category ? 'Other' : analysis.category;

          return (
            <button key={analysis.id} className="analysis-card analysis-card-refined" onClick={() => onOpen(analysis.id)}>
              <strong className="analysis-brand">{analysis.brand_name}</strong>
              <span className="analysis-meta">{getCategoryEmoji(emojiCategory)} {categoryLabel}</span>
              <span className="analysis-meta">{analysis.asset_count} assets</span>
              <span className="analysis-meta">{new Date(analysis.created_at).toLocaleDateString()}</span>
              <span className="status-pill status-tag">{analysis.status}</span>
            </button>
          );
        })}
      </div>

      {loading && <p className="status-message">Loading analyses...</p>}
      {!loading && analyses.length === 0 && (
        <p className="status-message">No analysis created yet. Start by creating your first brand analysis.</p>
      )}
    </section>
  );
}
