import { FormEvent, useEffect, useState } from 'react';

import { forgotPassword, login, me, signup, User } from './api/auth';

import { createAnalysis, getAnalysisDetail, listAnalyses, uploadAssets, Analysis, AnalysisDetail } from './api/analysis';
import { forgotPassword, login, me, signup, User } from './api/auth';

const ACCESS_TOKEN_KEY = 'brandradar_access_token';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const [darkMode, setDarkMode] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        setIsRestoringSession(false);
        return;
      }

      try {
        const user = await me(token);
        setCurrentUser(user);
      } catch {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      } finally {
        setIsRestoringSession(false);
      }
    };

    void restoreSession();
  }, []);

  const handleAuthenticated = (token: string, user: User) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
    setCurrentUser(user);
  };

  const handleLogout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setCurrentUser(null);
    setScreen('login');
  };

  return (
    <main className={`app-shell ${darkMode ? 'mode-dark' : ''}`}>
      <section className="panel">
        <header className="panel-top">
          <span className="logo">BrandRadar</span>
          <nav className="top-nav" aria-label="Access views">
            <button className={`nav-link ${screen === 'signup' ? 'active' : ''}`} onClick={() => setScreen('signup')}>
              SIGN UP
            </button>
            <button className={`nav-link ${screen === 'login' ? 'active' : ''}`} onClick={() => setScreen('login')}>
              LOGIN
            </button>
          </nav>
          <label className="dark-toggle">
            <span>DARK MODE</span>
            <input type="checkbox" checked={darkMode} onChange={() => setDarkMode(!darkMode)} />
          </label>
        </header>

        {isRestoringSession && <p className="status-message">Restoring session...</p>}

        {!isRestoringSession && currentUser && <AuthenticatedScreen user={currentUser} onLogout={handleLogout} />}

        {!isRestoringSession && !currentUser && screen === 'login' && (
          <LoginScreen
            onForgotPassword={() => setScreen('forgot-password')}
            onAuthenticated={(token, user) => handleAuthenticated(token, user)}
          />
        )}
        {!isRestoringSession && !currentUser && screen === 'signup' && (
          <SignupScreen onSwitchToLogin={() => setScreen('login')} />
        )}
        {!isRestoringSession && !currentUser && screen === 'forgot-password' && (
          <ForgotPasswordScreen onBackToLogin={() => setScreen('login')} />
        )}
      </section>
    </main>
  );
}

function LoginScreen({ onForgotPassword, onAuthenticated }: { onForgotPassword: () => void; onAuthenticated: (token: string, user: User) => void; }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const result = await login({ email, password });
      onAuthenticated(result.access_token, result.user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="content login-content">
      <h1>UNDERSTANDING YOUR BRAND UNIVERSE</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <p className="form-intro">Welcome back</p>
        <label htmlFor="login-email">EMAIL</label>
        <input id="login-email" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

        <label htmlFor="login-password">PASSWORD</label>
        <input id="login-password" name="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />

        {error && <p className="feedback feedback-error">{error}</p>}

        <button className="helper-link helper-link-button" type="button" onClick={onForgotPassword}>
          FORGOT YOUR PASSWORD?
        </button>
        <button className="primary-btn" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'AUTHENTICATING...' : 'ACCESS PANEL'}
        </button>
      </form>
    </section>
  );
}

function SignupScreen({ onSwitchToLogin }: { onSwitchToLogin: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [workRole, setWorkRole] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await signup({ name, email, password, work_role: workRole });
      setSuccess('Signup successful. You can now login.');
      setName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setWorkRole('');
      onSwitchToLogin();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Signup failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="content signup-content">
      <h1 className="signup-logo">BrandRadar</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="name">NAME</label>
        <input id="name" name="name" type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="email">EMAIL</label>
        <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

        <label htmlFor="password">PASSWORD</label>
        <input id="password" name="password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />

        <label htmlFor="confirm-password">CONFIRM PASSWORD</label>
        <input id="confirm-password" name="confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />

        <label htmlFor="work-role">WORK ROLE</label>
        <input id="work-role" name="work-role" type="text" autoComplete="organization-title" value={workRole} onChange={(e) => setWorkRole(e.target.value)} required />

        {error && <p className="feedback feedback-error">{error}</p>}
        {success && <p className="feedback feedback-success">{success}</p>}

        <button className="primary-btn" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'SUBMITTING...' : 'CREATE ACCESS'}
        </button>
      </form>
    </section>
  );
}

function ForgotPasswordScreen({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setIsSubmitting(true);

    try {
      const response = await forgotPassword({ email });
      setMessage(response.message);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Request failed');
    } finally {
      setIsSubmitting(false);
    }
  };

function ForgotPasswordScreen({ onBackToLogin }: { onBackToLogin: () => void }) { const [email,setEmail]=useState('');const [message,setMessage]=useState('');
  const handle=async(e:FormEvent)=>{e.preventDefault();const r=await forgotPassword({email});setMessage(r.message);};
  return <section className="content forgot-content"><h1 className="forgot-logo">BrandRadar</h1><form className="auth-form" onSubmit={handle}><h2 className="forgot-heading">Reset access</h2><p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required/><button className="primary-btn">SEND RECOVERY LINK</button>{message&&<p className="confirmation-text">{message}</p>}<button className="secondary-action" type="button" onClick={onBackToLogin}>Back to login</button></form></section>;}

        <label htmlFor="forgot-email">EMAIL</label>
        <input id="forgot-email" name="forgot-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required />

        <button className="primary-btn" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'SENDING...' : 'SEND RECOVERY LINK'}
        </button>

        {error && <p className="feedback feedback-error">{error}</p>}
        {message && <p className="confirmation-text">{message}</p>}

function AnalysisDetailScreen({ analysis, onBack }: { analysis: AnalysisDetail; onBack:()=>void }) {
  return <section className="content app-content"><h1 className="module-title">{analysis.brand_name}</h1><p>{analysis.custom_category||analysis.category} · {analysis.status} · {analysis.asset_count} assets · {new Date(analysis.created_at).toLocaleDateString()}</p><div className="asset-grid">{analysis.assets.map((asset)=><article key={asset.id} className="analysis-card">{asset.preview_path?<img src={`http://localhost:8000${asset.preview_path}`} alt={asset.original_filename} className="thumb"/>:<div className="thumb placeholder">PDF</div>}<strong>{asset.original_filename}</strong><span>{asset.file_type.toUpperCase()} · {asset.size_bytes} bytes</span><span>{asset.width && asset.height ? `${asset.width}x${asset.height}` : 'N/A'}</span></article>)}</div><button className="secondary-action" onClick={onBack}>Back to analyses</button></section>;
}

function AuthenticatedScreen({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <section className="content auth-success-content">
      <h1 className="signup-logo">BrandRadar</h1>
      <div className="auth-summary">
        <h2 className="forgot-heading">Access granted</h2>
        <p className="forgot-subtext">BrandRadar session active</p>
        <p><strong>User name:</strong> {user.name}</p>
        <p><strong>User email:</strong> {user.email}</p>
        <p><strong>User work role:</strong> {user.work_role}</p>
        <button className="primary-btn" type="button" onClick={onLogout}>Logout</button>
      </div>
    </section>
  );
}

export default App;
