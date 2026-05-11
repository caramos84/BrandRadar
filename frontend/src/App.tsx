import { FormEvent, useEffect, useState } from 'react';

import { forgotPassword, login, me, signup, User } from './api/auth';

type AuthScreen = 'login' | 'signup' | 'forgot-password';

const ACCESS_TOKEN_KEY = 'brandradar_token';

function App() {
  const [authScreen, setAuthScreen] = useState<AuthScreen>('login');
  const [darkMode, setDarkMode] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

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
        setAuthScreen('login');
      } finally {
        setIsRestoringSession(false);
      }
    };

    void restoreSession();
  }, []);

  const handleAuthenticated = (nextToken: string, user: User) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, nextToken);
    setToken(nextToken);
    setCurrentUser(user);
  };

  const handleLogout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    setToken(null);
    setCurrentUser(null);
    setAuthScreen('login');
  };

  return (
    <main className={`app-shell ${darkMode ? 'mode-dark' : ''}`}>
      <section className="panel">
        <header className="panel-top">
          <span className="logo">BrandRadar</span>

          {!currentUser ? (
            <nav className="top-nav" aria-label="Auth Navigation">
              <button className={`nav-link ${authScreen === 'signup' ? 'active' : ''}`} onClick={() => setAuthScreen('signup')}>
                SIGN UP
              </button>
              <button className={`nav-link ${authScreen === 'login' ? 'active' : ''}`} onClick={() => setAuthScreen('login')}>
                LOGIN
              </button>
            </nav>
          ) : (
            <div className="user-strip">
              <span>{currentUser.name} · {currentUser.email}</span>
              <button className="nav-link" onClick={handleLogout}>
                LOGOUT
              </button>
            </div>
          )}

          <label className="dark-toggle">
            <span>DARK MODE</span>
            <input type="checkbox" checked={darkMode} onChange={() => setDarkMode((prev) => !prev)} />
          </label>
        </header>

        {isRestoringSession && <p className="status-message">Restoring session...</p>}

        {!isRestoringSession && !currentUser && authScreen === 'login' && (
          <LoginScreen onForgotPassword={() => setAuthScreen('forgot-password')} onAuthenticated={handleAuthenticated} />
        )}

        {!isRestoringSession && !currentUser && authScreen === 'signup' && (
          <SignupScreen onSwitchToLogin={() => setAuthScreen('login')} />
        )}

        {!isRestoringSession && !currentUser && authScreen === 'forgot-password' && (
          <ForgotPasswordScreen onBackToLogin={() => setAuthScreen('login')} />
        )}

        {!isRestoringSession && currentUser && <AuthenticatedScreen user={currentUser} token={token} onLogout={handleLogout} />}
      </section>
    </main>
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

  return <section className="content signup-content"><h1 className="signup-logo">BrandRadar</h1><form className="auth-form" onSubmit={handleSubmit}><label>NAME</label><input value={name} onChange={(e)=>setName(e.target.value)} required /><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required /><label>PASSWORD</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} required /><label>CONFIRM PASSWORD</label><input type="password" value={confirmPassword} onChange={(e)=>setConfirmPassword(e.target.value)} required /><label>WORK ROLE</label><input value={workRole} onChange={(e)=>setWorkRole(e.target.value)} required />{error && <p className="feedback feedback-error">{error}</p>}{success && <p className="confirmation-text">{success}</p>}<button className="primary-btn" type="submit">CREATE ACCESS</button></form></section>;
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

  return <section className="content forgot-content"><h1 className="forgot-logo">BrandRadar</h1><form className="auth-form" onSubmit={handleSubmit}><h2 className="forgot-heading">Reset access</h2><p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p><label>EMAIL</label><input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} required /><button className="primary-btn" type="submit">SEND RECOVERY LINK</button>{message && <p className="confirmation-text">{message}</p>}{error && <p className="feedback feedback-error">{error}</p>}<button className="secondary-action" type="button" onClick={onBackToLogin}>Back to login</button></form></section>;
}

function AuthenticatedScreen({ user, token, onLogout }: { user: User; token: string | null; onLogout: () => void }) {
  return (
    <section className="content auth-success-content">
      <h1 className="signup-logo">BrandRadar</h1>
      <h2 className="forgot-heading">Access granted</h2>
      <p className="status-message">BrandRadar session active</p>

      <div className="auth-summary">
        <p><strong>Name:</strong> {user.name}</p>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Work role:</strong> {user.work_role}</p>
        {token && <p><strong>Session:</strong> active</p>}
      </div>

      <button className="primary-btn" type="button" onClick={onLogout}>Logout</button>
    </section>
  );
}

export default App;
