import { FormEvent, useState } from 'react';

type Screen = 'login' | 'signup' | 'forgot-password';

function App() {
  const [screen, setScreen] = useState<Screen>('login');
  const [darkMode, setDarkMode] = useState<boolean>(false);

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

        {screen === 'login' && <LoginScreen onForgotPassword={() => setScreen('forgot-password')} />}
        {screen === 'signup' && <SignupScreen />}
        {screen === 'forgot-password' && <ForgotPasswordScreen onBackToLogin={() => setScreen('login')} />}
      </section>
    </main>
  );
}

function LoginScreen({ onForgotPassword }: { onForgotPassword: () => void }) {
  return (
    <section className="content login-content">
      <h1>UNDERSTANDING YOUR BRAND UNIVERSE</h1>
      <form className="auth-form" onSubmit={(e) => e.preventDefault()}>
        <p className="form-intro">Welcome back</p>
        <label htmlFor="login-email">EMAIL</label>
        <input id="login-email" name="email" type="email" autoComplete="email" />

        <label htmlFor="login-password">PASSWORD</label>
        <input id="login-password" name="password" type="password" autoComplete="current-password" />

        <button className="helper-link helper-link-button" type="button" onClick={onForgotPassword}>
          FORGOT YOUR PASSWORD?
        </button>
        <button className="primary-btn" type="submit">
          ACCESS PANEL
        </button>
      </form>
    </section>
  );
}

function SignupScreen() {
  return (
    <section className="content signup-content">
      <h1 className="signup-logo">BrandRadar</h1>
      <form className="auth-form" onSubmit={(e) => e.preventDefault()}>
        <label htmlFor="name">NAME</label>
        <input id="name" name="name" type="text" autoComplete="name" />

        <label htmlFor="email">EMAIL</label>
        <input id="email" name="email" type="email" autoComplete="email" />

        <label htmlFor="password">PASSWORD</label>
        <input id="password" name="password" type="password" autoComplete="new-password" />

        <label htmlFor="confirm-password">CONFIRM PASSWORD</label>
        <input id="confirm-password" name="confirm-password" type="password" autoComplete="new-password" />

        <label htmlFor="work-role">WORK ROLE</label>
        <input id="work-role" name="work-role" type="text" autoComplete="organization-title" />

        <button className="primary-btn" type="submit">
          CREATE ACCESS
        </button>
      </form>
    </section>
  );
}

function ForgotPasswordScreen({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setShowConfirmation(true);
  };

  return (
    <section className="content forgot-content">
      <h1 className="forgot-logo">BrandRadar</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2 className="forgot-heading">Reset access</h2>
        <p className="forgot-subtext">Enter your email and we’ll prepare a recovery link.</p>

        <label htmlFor="forgot-email">EMAIL</label>
        <input id="forgot-email" name="forgot-email" type="email" autoComplete="email" />

        <button className="primary-btn" type="submit">
          SEND RECOVERY LINK
        </button>

        {showConfirmation && <p className="confirmation-text">If this email exists, a recovery link will be sent.</p>}

        <button className="secondary-action" type="button" onClick={onBackToLogin}>
          Back to login
        </button>
      </form>
    </section>
  );
}

export default App;
