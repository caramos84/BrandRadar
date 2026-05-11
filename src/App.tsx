import { useState } from 'react';

type Screen = 'login' | 'signup';

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

        {screen === 'login' ? <LoginScreen /> : <SignupScreen />}
      </section>
    </main>
  );
}

function LoginScreen() {
  return (
    <section className="content login-content">
      <h1>UNDERSTANDING YOUR BRAND UNIVERSE</h1>
      <form className="auth-form" onSubmit={(e) => e.preventDefault()}>
        <p className="form-intro">Welcome back</p>
        <label htmlFor="login-email">EMAIL</label>
        <input id="login-email" name="email" type="email" autoComplete="email" />

        <label htmlFor="login-password">PASSWORD</label>
        <input id="login-password" name="password" type="password" autoComplete="current-password" />

        <a className="helper-link" href="#" onClick={(e) => e.preventDefault()}>
          FORGOT YOUR PASSWORD?
        </a>
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

export default App;
