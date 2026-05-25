import { FormEvent, useEffect, useState } from 'react';

import { User, forgotPassword, login, me, signup } from './api/auth';
import { Analysis, AnalysisDetail, createAnalysis, getAnalysisDetail, listAnalyses, uploadAssets } from './api/analyses';
import { AnalysisDetailScreen } from './screens/AnalysisDetailScreen';
import { AnalysisListScreen } from './screens/AnalysisListScreen';
import { AnalysisDraft, CreateAnalysisScreen } from './screens/CreateAnalysisScreen';

type AuthScreen = 'login' | 'signup' | 'forgot-password';
type AppView = 'analysis-list' | 'create-analysis' | 'analysis-detail';

const ACCESS_TOKEN_KEY = 'brandradar_access_token';

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
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const restoreSession = async () => {
      const savedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!savedToken) {
        setIsRestoringSession(false);
        return;
      }

      try {
        const user = await me(savedToken);
        setToken(savedToken);
        setCurrentUser(user);
      } catch {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        setToken(null);
        setCurrentUser(null);
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
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : 'Could not load analyses.');
    } finally {
      setLoadingAnalyses(false);
    }
  };

  useEffect(() => {
    if (token) void refreshAnalyses(token);
  }, [token]);

  const handleAuthenticated = (nextToken: string, user: User) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, nextToken);
    setToken(nextToken);
    setCurrentUser(user);
    setView('analysis-list');
    setSelectedAnalysis(null);
  };

  const handleLogout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setToken(null);
    setCurrentUser(null);
    setAuthScreen('login');
    setView('analysis-list');
    setSelectedAnalysis(null);
  };

  const handleOpenAnalysis = async (analysisId: number) => {
    if (!token) return;

    setAnalysisError('');
    try {
      const detail = await getAnalysisDetail(token, analysisId);
      setSelectedAnalysis(detail);
      setView('analysis-detail');
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : 'Could not open analysis.');
    }
  };

  const handleCreateAnalysis = async (draft: AnalysisDraft) => {
    if (!token) return;

    setIsProcessing(true);
    setAnalysisError('');

    try {
      const created = await createAnalysis(token, {
        brand_name: draft.brandName,
        category: draft.category,
        custom_category: draft.category === 'Other' ? draft.customCategory : null,
      });

      await uploadAssets(token, created.id, draft.files);
      await refreshAnalyses(token);
      setView('analysis-list');
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : 'Failed to create analysis.');
    } finally {
      setIsProcessing(false);
    }
  };

  const shellClass = currentUser ? 'workspace-shell' : 'auth-shell';

  return (
    <main className={`app-shell ${shellClass} ${darkMode ? 'mode-dark' : ''}`}>
      <section className="panel">
        <header className="panel-top">
          <><img className="app-logo app-logo-dark" src="/brandradar-logo-dark.svg" alt="BrandRadar" /><img className="app-logo app-logo-light" src="/brandradar-logo-light.svg" alt="BrandRadar" /></>

          {!currentUser ? (
            <nav className="top-nav" aria-label="Auth Navigation">
              <button className={`nav-link ${authScreen === 'signup' ? 'active' : ''}`} onClick={() => setAuthScreen('signup')}>SIGN UP</button>
              <button className={`nav-link ${authScreen === 'login' ? 'active' : ''}`} onClick={() => setAuthScreen('login')}>LOGIN</button>
            </nav>
          ) : (
            <div className="user-module">
              <div className="user-module-info">
                <div className="user-module-text">
                  <span className="user-module-name">{currentUser.name}</span>
                  <span className="user-module-email">{currentUser.email}</span>
                </div>
                <div className="user-module-avatar" aria-hidden="true">
                  {currentUser.name?.charAt(0).toUpperCase() || 'U'}
                </div>
              </div>
              <div className="user-module-actions">
                <button type="button" className="user-module-link">PROFILE</button>
                <button type="button" className="user-module-link">SETTINGS</button>
                <button type="button" className="user-module-link user-module-exit" onClick={handleLogout}>EXIT</button>
              </div>
            </div>
          )}
        </header>

        {isRestoringSession && <p className="status-message">Restoring session...</p>}

        {!isRestoringSession && !currentUser && authScreen === 'login' && (
          <>
            <LoginScreen onForgotPassword={() => setAuthScreen('forgot-password')} onAuthenticated={handleAuthenticated} />
            <footer className="powered-footer">
              <span>Powered by</span>
              <img className="op-logo op-logo-light" src="/OP-LOGO-light.svg" alt="Omnicom Production" />
              <img className="op-logo op-logo-dark" src="/OP-LOGO-dark.svg" alt="Omnicom Production" />
            </footer>
          </>
        )}
        {!isRestoringSession && !currentUser && authScreen === 'signup' && (
          <>
            <SignupScreen onSwitchToLogin={() => setAuthScreen('login')} />
            <footer className="powered-footer">
              <span>Powered by</span>
              <img className="op-logo op-logo-light" src="/OP-LOGO-light.svg" alt="Omnicom Production" />
              <img className="op-logo op-logo-dark" src="/OP-LOGO-dark.svg" alt="Omnicom Production" />
            </footer>
          </>
        )}
        {!isRestoringSession && !currentUser && authScreen === 'forgot-password' && (
          <>
            <ForgotPasswordScreen onBackToLogin={() => setAuthScreen('login')} />
            <footer className="powered-footer">
              <span>Powered by</span>
              <img className="op-logo op-logo-light" src="/OP-LOGO-light.svg" alt="Omnicom Production" />
              <img className="op-logo op-logo-dark" src="/OP-LOGO-dark.svg" alt="Omnicom Production" />
            </footer>
          </>
        )}

        {!isRestoringSession && currentUser && token && view === 'analysis-list' && (
          <AnalysisListScreen
            analyses={analyses}
            loading={loadingAnalyses}
            error={analysisError}
            onCreate={() => setView('create-analysis')}
            onOpen={handleOpenAnalysis}
            token={token}
            onRefresh={() => void refreshAnalyses(token)}
          />
        )}

        {!isRestoringSession && currentUser && token && view === 'create-analysis' && (
          <section className="content">
            {isProcessing ? (
              <ProcessingScreen />
            ) : (
              <CreateAnalysisScreen
                onBack={() => setView('analysis-list')}
                onSubmit={handleCreateAnalysis}
                error={analysisError}
                isProcessing={isProcessing}
              />
            )}
          </section>
        )}

        {!isRestoringSession && currentUser && token && view === 'analysis-detail' && selectedAnalysis && (
          <AnalysisDetailScreen analysis={selectedAnalysis} token={token} onBack={() => setView('analysis-list')} />
        )}
      </section>

      <div className="floating-theme-switch" aria-label="Toggle dark mode">
        <label className="theme-switch" aria-hidden="true">
          <span>DARK MODE</span>
          <input type="checkbox" checked={darkMode} onChange={() => setDarkMode((prev) => !prev)} />
          <span className="switch-track">
            <span className="switch-thumb" />
          </span>
        </label>
      </div>
    </main>
  );
}

function ProcessingScreen() {
  return (
    <section className="content processing">
      <img className="auth-logo" src="/brandradar-logo-light.svg" alt="BrandRadar" />
      <h2 className="forgot-heading">Processing your files</h2>
      <div className="loader" />
      <ul>
        <li>Reading files</li>
        <li>Extracting metadata</li>
        <li>Saving assets</li>
        <li>Building analysis index</li>
      </ul>
    </section>
  );
}

function LoginScreen({ onForgotPassword, onAuthenticated }: { onForgotPassword: () => void; onAuthenticated: (token: string, user: User) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    try {
      const result = await login({ email, password });
      onAuthenticated(result.access_token, result.user);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Login failed.');
    }
  };

  return <section className="content login-content"><h1>UNDERSTANDING YOUR BRAND UNIVERSE</h1><form className="auth-form" onSubmit={handleSubmit}><p className="form-intro">Welcome back</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required /><label>PASSWORD</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required />{error && <p className="feedback feedback-error">{error}</p>}<button className="helper-link helper-link-button" type="button" onClick={onForgotPassword}>FORGOT YOUR PASSWORD?</button><button className="primary-btn" type="submit">ACCESS PANEL</button></form></section>;
}

function SignupScreen({ onSwitchToLogin }: { onSwitchToLogin: () => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [workRole, setWorkRole] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    try {
      await signup({ name, email, password, work_role: workRole });
      setSuccess('Access created. You can now log in.');
      setTimeout(onSwitchToLogin, 700);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Signup failed.');
    }
  };

  return <section className="content signup-content"><img className="auth-logo" src="/brandradar-logo-light.svg" alt="BrandRadar" /><form className="auth-form" onSubmit={handleSubmit}><label>NAME</label><input value={name} onChange={(e)=>setName(e.target.value)} required /><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required /><label>PASSWORD</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required /><label>CONFIRM PASSWORD</label><input type="password" value={confirmPassword} onChange={(e)=>setConfirmPassword(e.target.value)} required /><label>WORK ROLE</label><input value={workRole} onChange={(e)=>setWorkRole(e.target.value)} required />{error && <p className="feedback feedback-error">{error}</p>}{success && <p className="confirmation-text">{success}</p>}<button className="primary-btn" type="submit">CREATE ACCESS</button></form></section>;
}

function ForgotPasswordScreen({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage('');
    setError('');

    try {
      const result = await forgotPassword({ email });
      setMessage(result.message);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Request failed.');
    }
  };

  return <section className="content forgot-content"><img className="auth-logo" src="/brandradar-logo-light.svg" alt="BrandRadar" /><form className="auth-form" onSubmit={handleSubmit}><h2 className="forgot-heading">Reset access</h2><p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required /><button className="primary-btn" type="submit">SEND RECOVERY LINK</button>{message && <p className="confirmation-text">{message}</p>}{error && <p className="feedback feedback-error">{error}</p>}<button className="secondary-action" type="button" onClick={onBackToLogin}>Back to login</button></form></section>;
}

export default App;
