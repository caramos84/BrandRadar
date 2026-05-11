import { FormEvent, useEffect, useState } from 'react';
import { forgotPassword, login, me, signup, User } from './api/auth';

type Screen = 'login' | 'signup' | 'forgot-password';

const ACCESS_TOKEN_KEY = 'brandradar_access_token';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const [darkMode, setDarkMode] = useState(false);
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

          {!currentUser && (
            <nav className="top-nav" aria-label="Access views">
              <button className={`nav-link ${screen === 'signup' ? 'active' : ''}`} onClick={() => setScreen('signup')}>
                SIGN UP
              </button>
              <button className={`nav-link ${screen === 'login' ? 'active' : ''}`} onClick={() => setScreen('login')}>
                LOGIN
              </button>
            </nav>
          )}

          <label className="dark-toggle">
            <span>DARK MODE</span>
            <input type="checkbox" checked={darkMode} onChange={() => setDarkMode(!darkMode)} />
          </label>
        </header>

        {isRestoringSession && <p className="status-message">Restoring session...</p>}

        {!isRestoringSession && currentUser && (
          <AuthenticatedScreen user={currentUser} onLogout={handleLogout} />
        )}

        {!isRestoringSession && !currentUser && screen === 'login' && (
          <LoginScreen
            onForgotPassword={() => setScreen('forgot-password')}
            onAuthenticated={handleAuthenticated}
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

function LoginScreen({
  onForgotPassword,
  onAuthenticated,
}: {
  onForgotPassword: () => void;
  onAuthenticated: (token: string, user: User) => void;
}) {
  const [email, setEmail] = useState('carlos@test.com');
  const [password, setPassword] = useState('test1234');
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
        <input
          id="login-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="login-password">PASSWORD</label>
        <input
          id="login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />

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
      setTimeout(onSwitchToLogin, 700);
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
        <input id="name" type="text" value={name} onChange={(event) => setName(event.target.value)} required />

        <label htmlFor="email">EMAIL</label>
        <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />

        <label htmlFor="password">PASSWORD</label>
        <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />

        <label htmlFor="confirm-password">CONFIRM PASSWORD</label>
        <input id="confirm-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required />

        <label htmlFor="work-role">WORK ROLE</label>
        <input id="work-role" type="text" value={workRole} onChange={(event) => setWorkRole(event.target.value)} required />

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

  return (
    <section className="content forgot-content">
      <h1 className="forgot-logo">BrandRadar</h1>

      <form className="auth-form" onSubmit={handleSubmit}>
        <h2 className="forgot-heading">Reset access</h2>
        <p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p>

        <label htmlFor="forgot-email">EMAIL</label>
        <input
          id="forgot-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <button className="primary-btn" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'SENDING...' : 'SEND RECOVERY LINK'}
        </button>

        {error && <p className="feedback feedback-error">{error}</p>}
        {message && <p className="confirmation-text">{message}</p>}

        <button className="secondary-action" type="button" onClick={onBackToLogin}>
          Back to login
        </button>
      </form>
    </section>
  );
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

        <button className="primary-btn" type="button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </section>
  );
}

export default App;