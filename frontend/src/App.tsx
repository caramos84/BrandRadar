import { DragEvent, FormEvent, useEffect, useMemo, useState } from 'react';

import { createAnalysis, getAnalysisDetail, listAnalyses, uploadAssets, Analysis, AnalysisDetail } from './api/analysis';
import { forgotPassword, login, me, signup, User } from './api/auth';

type AuthScreen = 'login' | 'signup' | 'forgot-password';
type AppView = 'analysis-list' | 'create-analysis' | 'processing' | 'analysis-detail';

const ACCESS_TOKEN_KEY = 'brandradar_access_token';
const CATEGORIES = ['Retail','Drinks & Spirits','Food','Fashion / Wear','Vehicles','Pharma','Convenience','Electronics / Mobile','Toys','Office','Furniture','Bank / Fintech','Real Estate','Software / Devs','Entertainment','Services','Transport','Communications','Industry','Pets','Other'];

function App() {
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');
  const [darkMode, setDarkMode] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  const [view, setView] = useState<AppView>('analysis-list');
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisDetail | null>(null);
  const [loadingAnalyses, setLoadingAnalyses] = useState(false);
  const [analysisError, setAnalysisError] = useState('');

  useEffect(() => {
    const restoreSession = async () => {
      const savedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!savedToken) return setIsRestoringSession(false);
      try {
        const user = await me(savedToken);
        setToken(savedToken);
        setCurrentUser(user);
      } catch {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      } finally {
        setIsRestoringSession(false);
      }
    };
    void restoreSession();
  }, []);

  const refreshAnalyses = async (activeToken: string) => {
    setLoadingAnalyses(true);
    setAnalysisError('');
    try {
      const items = await listAnalyses(activeToken);
      setAnalyses(items);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : 'Could not load analyses');
    } finally {
      setLoadingAnalyses(false);
    }
  };

  useEffect(() => { if (token) void refreshAnalyses(token); }, [token]);

  const handleAuthenticated = (nextToken: string, user: User) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, nextToken);
    setToken(nextToken);
    setCurrentUser(user);
    setView('analysis-list');
  };

  const handleLogout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setToken(null); setCurrentUser(null); setAuthScreen('login'); setView('analysis-list');
  };

  const openAnalysis = async (analysisId: number) => {
    if (!token) return;
    const detail = await getAnalysisDetail(token, analysisId);
    setSelectedAnalysis(detail);
    setView('analysis-detail');
  };

  return <main className={`app-shell ${darkMode ? 'mode-dark' : ''}`}><section className="panel">
    <header className="panel-top"><span className="logo">BrandRadar</span>
      {!currentUser ? <nav className="top-nav"><button className={`nav-link ${authScreen==='signup'?'active':''}`} onClick={()=>setAuthScreen('signup')}>SIGN UP</button><button className={`nav-link ${authScreen==='login'?'active':''}`} onClick={()=>setAuthScreen('login')}>LOGIN</button></nav>
      : <div className="user-strip"><span>{currentUser.name} · {currentUser.email}</span><button className="nav-link" onClick={handleLogout}>LOGOUT</button></div>}
      <label className="dark-toggle"><span>DARK MODE</span><input type="checkbox" checked={darkMode} onChange={()=>setDarkMode(!darkMode)} /></label></header>

    {isRestoringSession && <p className="status-message">Restoring session...</p>}
    {!isRestoringSession && !currentUser && authScreen==='login' && <LoginScreen onForgotPassword={()=>setAuthScreen('forgot-password')} onAuthenticated={handleAuthenticated} />}
    {!isRestoringSession && !currentUser && authScreen==='signup' && <SignupScreen onSwitchToLogin={()=>setAuthScreen('login')} />}
    {!isRestoringSession && !currentUser && authScreen==='forgot-password' && <ForgotPasswordScreen onBackToLogin={()=>setAuthScreen('login')} />}

    {!isRestoringSession && currentUser && token && view==='analysis-list' && <AnalysisListScreen analyses={analyses} loading={loadingAnalyses} error={analysisError} onCreate={()=>setView('create-analysis')} onOpen={openAnalysis} />}
    {!isRestoringSession && currentUser && token && view==='create-analysis' && <CreateAnalysisScreen token={token} onCancel={()=>setView('analysis-list')} onProcessing={()=>setView('processing')} onDone={async()=>{await refreshAnalyses(token); setView('analysis-list');}} />}
    {!isRestoringSession && currentUser && view==='processing' && <ProcessingScreen />}
    {!isRestoringSession && currentUser && view==='analysis-detail' && selectedAnalysis && <AnalysisDetailScreen analysis={selectedAnalysis} onBack={()=>setView('analysis-list')} />}
  </section></main>;
}

function LoginScreen({ onForgotPassword, onAuthenticated }: { onForgotPassword: () => void; onAuthenticated: (token: string, user: User) => void; }) { /* same as before */
  const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [error,setError]=useState('');
  const handleSubmit=async(e:FormEvent)=>{e.preventDefault();setError('');try{const r=await login({email,password});onAuthenticated(r.access_token,r.user);}catch(err){setError(err instanceof Error?err.message:'Login failed');}};
  return <section className="content login-content"><h1>UNDERSTANDING YOUR BRAND UNIVERSE</h1><form className="auth-form" onSubmit={handleSubmit}><p className="form-intro">Welcome back</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required/><label>PASSWORD</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required/>{error&&<p className="feedback feedback-error">{error}</p>}<button className="helper-link helper-link-button" type="button" onClick={onForgotPassword}>FORGOT YOUR PASSWORD?</button><button className="primary-btn" type="submit">ACCESS PANEL</button></form></section>;
}

function SignupScreen({ onSwitchToLogin }: { onSwitchToLogin: () => void }) { const [name,setName]=useState('');const [email,setEmail]=useState('');const [password,setPassword]=useState('');const [confirm,setConfirm]=useState('');const [workRole,setWorkRole]=useState('');const [error,setError]=useState('');
  const handle=async(e:FormEvent)=>{e.preventDefault(); setError(''); if(password!==confirm){setError('Passwords do not match.');return;} try{await signup({name,email,password,work_role:workRole});onSwitchToLogin();}catch(err){setError(err instanceof Error?err.message:'Signup failed');}};
  return <section className="content signup-content"><h1 className="signup-logo">BrandRadar</h1><form className="auth-form" onSubmit={handle}><label>NAME</label><input value={name} onChange={(e)=>setName(e.target.value)} required/><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required/><label>PASSWORD</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required/><label>CONFIRM PASSWORD</label><input type="password" value={confirm} onChange={(e)=>setConfirm(e.target.value)} required/><label>WORK ROLE</label><input value={workRole} onChange={(e)=>setWorkRole(e.target.value)} required/>{error&&<p className="feedback feedback-error">{error}</p>}<button className="primary-btn">CREATE ACCESS</button></form></section>; }

function ForgotPasswordScreen({ onBackToLogin }: { onBackToLogin: () => void }) { const [email,setEmail]=useState('');const [message,setMessage]=useState('');
  const handle=async(e:FormEvent)=>{e.preventDefault();const r=await forgotPassword({email});setMessage(r.message);};
  return <section className="content forgot-content"><h1 className="forgot-logo">BrandRadar</h1><form className="auth-form" onSubmit={handle}><h2 className="forgot-heading">Reset access</h2><p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required/><button className="primary-btn">SEND RECOVERY LINK</button>{message&&<p className="confirmation-text">{message}</p>}<button className="secondary-action" type="button" onClick={onBackToLogin}>Back to login</button></form></section>;}

function AnalysisListScreen({ analyses, loading, error, onCreate, onOpen }: { analyses: Analysis[]; loading:boolean; error:string; onCreate:()=>void; onOpen:(id:number)=>void; }) {
  return <section className="content app-content"><h1 className="module-title">YOUR ANALYSIS</h1>{error&&<p className="feedback feedback-error">{error}</p>}<div className="analysis-grid"><button className="analysis-card create-card" onClick={onCreate}>Create New Analysis</button>{analyses.map((a)=><button key={a.id} className="analysis-card" onClick={()=>onOpen(a.id)}><strong>{a.brand_name}</strong><span>{a.custom_category||a.category}</span><span>{new Date(a.created_at).toLocaleDateString()}</span><span>{a.asset_count} assets</span><span className="status-pill">{a.status}</span></button>)}</div>{!loading&&analyses.length===0&&<p className="status-message">No analysis created yet. Start by creating your first brand analysis.</p>}</section>;
}

function CreateAnalysisScreen({ token, onCancel, onProcessing, onDone }: { token:string; onCancel:()=>void; onProcessing:()=>void; onDone:()=>Promise<void>; }) {
  const [brandName,setBrandName]=useState(''); const [category,setCategory]=useState(CATEGORIES[0]); const [customCategory,setCustomCategory]=useState(''); const [files,setFiles]=useState<File[]>([]); const [error,setError]=useState('');
  const breakdown = useMemo(()=>files.reduce<Record<string,number>>((acc,f)=>{const k=f.name.split('.').pop()?.toUpperCase()||'OTHER';acc[k]=(acc[k]||0)+1;return acc;},{}),[files]);
  const handleFiles=(list:FileList|null)=>{if(!list) return; setFiles(Array.from(list));};
  const handleDrop=(e:DragEvent)=>{e.preventDefault(); handleFiles(e.dataTransfer.files);};
  const submit=async(e:FormEvent)=>{e.preventDefault(); setError(''); if(!files.length){setError('Please select at least one file.');return;} onProcessing(); try{const analysis=await createAnalysis(token,{brand_name:brandName,category,custom_category:category==='Other'?customCategory:null}); await uploadAssets(token,analysis.id,files); await onDone();}catch(err){setError(err instanceof Error?err.message:'Failed to create analysis'); onCancel();}};
  return <section className="content create-layout"><div><h1>START YOUR BRAND ANALYSIS</h1></div><form className="auth-form" onSubmit={submit}><label>NAME YOUR BRAND</label><input value={brandName} onChange={(e)=>setBrandName(e.target.value)} required/><label>CATEGORY</label><select value={category} onChange={(e)=>setCategory(e.target.value)}>{CATEGORIES.map((c)=><option key={c}>{c}</option>)}</select>{category==='Other'&&<><label>CUSTOM CATEGORY</label><input value={customCategory} onChange={(e)=>setCustomCategory(e.target.value)} required/></>}<label>UPLOAD FILES</label><div className="dropzone" onDragOver={(e)=>e.preventDefault()} onDrop={handleDrop}><p>Drag and drop files here</p><p>JPG · PNG · PDF</p><input type="file" multiple accept=".jpg,.jpeg,.png,.pdf" onChange={(e)=>handleFiles(e.target.files)} /></div><p>{files.length} file(s) selected</p><p>{Object.entries(breakdown).map(([k,v])=>`${k}: ${v}`).join(' · ')}</p>{error&&<p className="feedback feedback-error">{error}</p>}<div><button className="primary-btn" type="submit">SUBMIT ANALYSIS</button><button className="secondary-action" type="button" onClick={onCancel}>Back</button></div></form></section>;
}

function ProcessingScreen(){return <section className="content processing"><h1 className="signup-logo">BrandRadar</h1><h2 className="forgot-heading">Processing your files</h2><div className="loader"/><ul><li>Reading files</li><li>Extracting metadata</li><li>Saving assets</li><li>Building analysis index</li></ul></section>;}

function AnalysisDetailScreen({ analysis, onBack }: { analysis: AnalysisDetail; onBack:()=>void }) {
  return <section className="content app-content"><h1 className="module-title">{analysis.brand_name}</h1><p>{analysis.custom_category||analysis.category} · {analysis.status} · {analysis.asset_count} assets · {new Date(analysis.created_at).toLocaleDateString()}</p><div className="asset-grid">{analysis.assets.map((asset)=><article key={asset.id} className="analysis-card">{asset.preview_path?<img src={`http://localhost:8000${asset.preview_path}`} alt={asset.original_filename} className="thumb"/>:<div className="thumb placeholder">PDF</div>}<strong>{asset.original_filename}</strong><span>{asset.file_type.toUpperCase()} · {asset.size_bytes} bytes</span><span>{asset.width && asset.height ? `${asset.width}x${asset.height}` : 'N/A'}</span></article>)}</div><button className="secondary-action" onClick={onBack}>Back to analyses</button></section>;
}

export default App;
