import { DragEvent, FormEvent, useMemo, useState } from 'react';

export type AnalysisDraft = {
  brandName: string;
  category: string;
  customCategory: string;
  files: File[];
};

type Props = {
  onBack: () => void;
  onSubmit: (draft: AnalysisDraft) => Promise<void>;
  error: string;
  isProcessing: boolean;
};

const CATEGORIES = ['Retail','Drinks & Spirits','Food','Fashion / Wear','Vehicles','Pharma','Convenience','Electronics / Mobile','Toys','Office','Furniture','Bank / Fintech','Real Estate','Software / Devs','Entertainment','Services','Transport','Communications','Industry','Pets','Other'];

export function CreateAnalysisScreen({ onBack, onSubmit, error, isProcessing }: Props) {
  const [brandName, setBrandName] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [customCategory, setCustomCategory] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [localError, setLocalError] = useState('');

  const breakdown = useMemo(() => files.reduce<Record<string, number>>((acc, file) => {
    const ext = file.name.split('.').pop()?.toUpperCase() ?? 'OTHER';
    acc[ext] = (acc[ext] ?? 0) + 1;
    return acc;
  }, {}), [files]);

  const handleFiles = (list: FileList | null) => {
    if (!list) return;
    setFiles(Array.from(list));
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    handleFiles(event.dataTransfer.files);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError('');

    if (!brandName.trim()) return setLocalError('Please enter your brand name.');
    if (files.length === 0) return setLocalError('Please select at least one file.');
    if (category === 'Other' && !customCategory.trim()) return setLocalError('Please enter a custom category.');

    await onSubmit({ brandName: brandName.trim(), category, customCategory: customCategory.trim(), files });
  };

  return (
    <section className="content create-layout">
      <div><h1>START YOUR BRAND ANALYSIS</h1></div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>NAME YOUR BRAND</label>
        <input value={brandName} onChange={(e) => setBrandName(e.target.value)} required />

        <label>CATEGORY</label>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((item) => <option key={item}>{item}</option>)}
        </select>

        {category === 'Other' && (
          <>
            <label>CUSTOM CATEGORY</label>
            <input value={customCategory} onChange={(e) => setCustomCategory(e.target.value)} required />
          </>
        )}

        <label>UPLOAD FILES</label>
        <div className="dropzone" onDragOver={(e) => e.preventDefault()} onDrop={handleDrop}>
          <p>Drag and drop files here</p>
          <p>JPG · PNG · PDF</p>
          <input type="file" multiple accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => handleFiles(e.target.files)} />
        </div>

        <p>{files.length} file(s) selected</p>
        {files.length > 0 && <p>{Object.entries(breakdown).map(([ext, count]) => `${ext}: ${count}`).join(' · ')}</p>}

        {localError && <p className="feedback feedback-error">{localError}</p>}
        {error && <p className="feedback feedback-error">{error}</p>}

        <div>
          <button className="primary-btn" type="submit" disabled={isProcessing}>SUBMIT ANALYSIS</button>
          <button className="secondary-action" type="button" onClick={onBack}>Back</button>
        </div>
      </form>
    </section>
  );
}
