import { useState } from 'react';
import { api, isMock } from '../api';

const EMPTY = { username: '', email: '', password: '', confirm: '' };

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login'); // login | register
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const isLogin = mode === 'login';
  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const switchMode = (next) => {
    setMode(next);
    setError('');
  };

  async function submit(e) {
    e.preventDefault();
    const email = form.email.trim();
    const username = form.username.trim();

    if (isLogin && (!email || !form.password)) return setError('Enter your email and password.');
    if (!isLogin && (!username || !email || !form.password || !form.confirm)) return setError('Fill in all fields.');
    if (!isLogin && form.password !== form.confirm) return setError("Passwords don't match.");

    setBusy(true);
    setError('');
    try {
      const user = isLogin
        ? await api.login({ email, password: form.password })
        : await api.register({ email, password: form.password, username });
      onAuth(user);
    } catch (err) {
      setError(capitalize(err.message));
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth-inner">
        <div className="brand brand--large">
          <span className="brand-mark" aria-hidden="true">👽</span>
          ImmHelp
        </div>
        <h1 className="auth-title">Moving to Cyprus, one question at a time</h1>
        <p className="auth-lede">
          Ask about visas, residence permits, transport and housing. Answers are drawn from official documents.
        </p>

        <div className="segmented" role="tablist" aria-label="Account">
          <button role="tab" aria-selected={isLogin} onClick={() => switchMode('login')}>
            Log in
          </button>
          <button role="tab" aria-selected={!isLogin} onClick={() => switchMode('register')}>
            Create account
          </button>
        </div>

        <form className="auth-form" onSubmit={submit} noValidate>
          {!isLogin && (
            <label className="field">
              <span>Name</span>
              <input value={form.username} onChange={update('username')} autoComplete="name" placeholder="John Doe" />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input type="email" value={form.email} onChange={update('email')} autoComplete="email" placeholder="you@example.com" />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={form.password}
              onChange={update('password')}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
            />
          </label>
          {!isLogin && (
            <label className="field">
              <span>Confirm password</span>
              <input type="password" value={form.confirm} onChange={update('confirm')} autoComplete="new-password" />
            </label>
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary btn-block" disabled={busy}>
            {busy ? (isLogin ? 'Logging in…' : 'Creating account…') : isLogin ? 'Log in' : 'Create account'}
          </button>
        </form>

        {isMock && (
          <p className="auth-hint">
            Mock mode: log in as <code>demo@immhelp.cy</code> / <code>demo1234</code>
          </p>
        )}
      </div>
    </div>
  );
}

function capitalize(s) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}
