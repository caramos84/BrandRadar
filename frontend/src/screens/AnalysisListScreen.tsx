import { useState } from 'react';
import { Analysis, updateAnalysis, deleteAnalysis } from '../api/analyses';

type Props = {
  analyses: Analysis[];
  loading: boolean;
  error: string;
  onCreate: () => void;
  onOpen: (analysisId: number) => void;
  token: string;
  onRefresh: () => void;
};

type EditingAnalysis = {
  id: number;
  brand_name: string;
  category: string;
  custom_category: string | null;
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

const CATEGORIES = Object.keys(CATEGORY_EMOJI);

function getCategoryEmoji(category: string) {
  return CATEGORY_EMOJI[category] ?? '✨';
}

export function AnalysisListScreen({ analyses, loading, error, onCreate, onOpen, token, onRefresh }: Props) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<EditingAnalysis | null>(null);
  const [editError, setEditError] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null);

  const handleEditClick = (e: React.MouseEvent, analysis: Analysis) => {
    e.stopPropagation();
    setEditingId(analysis.id);
    setEditData({
      id: analysis.id,
      brand_name: analysis.brand_name,
      category: analysis.category,
      custom_category: analysis.custom_category,
    });
    setEditError('');
  };

  const handleEditSave = async () => {
    if (!editData) return;
    setEditError('');

    try {
      await updateAnalysis(token, editData.id, {
        brand_name: editData.brand_name.trim(),
        category: editData.category,
        custom_category: editData.custom_category,
      });
      setEditingId(null);
      setEditData(null);
      onRefresh();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Failed to save');
    }
  };

  const handleDeleteClick = async (e: React.MouseEvent, analysisId: number) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this analysis? This action cannot be undone.')) return;

    setDeleting(analysisId);
    try {
      await deleteAnalysis(token, analysisId);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    } finally {
      setDeleting(null);
    }
  };

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
          const isEditing = editingId === analysis.id;

          return (
            <div key={analysis.id} className="analysis-card analysis-card-refined analysis-card-wrapper">
              {isEditing && editData ? (
                <div className="analysis-edit-form" onClick={(e) => e.stopPropagation()}>
                  {editError && <p className="feedback feedback-error">{editError}</p>}
                  <label>
                    <span className="form-label">Brand Name</span>
                    <input
                      type="text"
                      value={editData.brand_name}
                      onChange={(e) => setEditData({ ...editData, brand_name: e.target.value })}
                      className="edit-input"
                    />
                  </label>
                  <label>
                    <span className="form-label">Category</span>
                    <select
                      value={editData.category}
                      onChange={(e) => setEditData({ ...editData, category: e.target.value })}
                      className="edit-select"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="form-label">Custom Category (optional)</span>
                    <input
                      type="text"
                      value={editData.custom_category || ''}
                      onChange={(e) => setEditData({ ...editData, custom_category: e.target.value || null })}
                      placeholder="Leave blank to use category"
                      className="edit-input"
                    />
                  </label>
                  <div className="edit-form-actions">
                    <button className="edit-btn edit-save-btn" onClick={handleEditSave}>
                      SAVE
                    </button>
                    <button className="edit-btn edit-cancel-btn" onClick={() => setEditingId(null)}>
                      CANCEL
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <button className="analysis-card-button" onClick={() => onOpen(analysis.id)}>
                    <strong className="analysis-brand">{analysis.brand_name}</strong>
                    <span className="analysis-meta">{getCategoryEmoji(emojiCategory)} {categoryLabel}</span>
                    <span className="analysis-meta">{analysis.asset_count} assets</span>
                    <span className="analysis-meta">{new Date(analysis.created_at).toLocaleDateString()}</span>
                    <span className="status-pill status-tag">{analysis.status}</span>
                  </button>
                  <div className="analysis-card-actions">
                    <button
                      className="analysis-action-btn analysis-edit-btn"
                      onClick={(e) => handleEditClick(e, analysis)}
                      title="Edit analysis"
                    >
                      ✎
                    </button>
                    <button
                      className="analysis-action-btn analysis-delete-btn"
                      onClick={(e) => handleDeleteClick(e, analysis.id)}
                      disabled={deleting === analysis.id}
                      title="Delete analysis"
                    >
                      {deleting === analysis.id ? '…' : '✕'}
                    </button>
                  </div>
                </>
              )}
            </div>
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
