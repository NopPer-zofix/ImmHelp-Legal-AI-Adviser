import { useEffect, useState } from 'react';
import { AUTH_LOST_EVENT } from './api/http';
import AuthPage from './components/AuthPage';
import ChatApp from './components/ChatApp';
import AdminApp from './components/admin/AdminApp';
import NoAccess from './components/NoAccess';
import { session } from './lib/storage';
import { isMock } from './api';
import { isAdmin } from './lib/roles';
import { useHashRoute, navigate } from './hooks/useHashRoute';

export default function App() {
  // Remembered across refreshes — Streamlit logged you out on every reload
  const [user, setUser] = useState(session.load);
  const [authNotice, setAuthNotice] = useState('');
  const route = useHashRoute();

  const signIn = (u) => {
    session.save(u);
    setAuthNotice('');
    setUser(u);
  };

  const signOut = () => {
    session.clear();
    window.history.replaceState(null, '', window.location.pathname);
    setUser(null);
  };

  // Expired token or banned account: back to the login screen with the server's reason
  useEffect(() => {
    const onLost = (e) => {
      session.clear();
      window.history.replaceState(null, '', window.location.pathname);
      setAuthNotice(e.detail);
      setUser(null);
    };
    window.addEventListener(AUTH_LOST_EVENT, onLost);
    return () => window.removeEventListener(AUTH_LOST_EVENT, onLost);
  }, []);

  // Sessions saved before the backend issued tokens can't call the API any more
  useEffect(() => {
    if (user && !user.token && !isMock) {
      session.clear();
      setAuthNotice('Please log in again.');
      setUser(null);
    }
  }, [user]);

  if (!user) return <AuthPage onAuth={signIn} notice={authNotice} />;

  if (route.startsWith('/admin')) {
    // UI gate only — the server rejects admin API calls from non-admins regardless
    if (!isAdmin(user)) return <NoAccess onBack={() => navigate('/')} />;
    return <AdminApp key={user.id} user={user} route={route} onLogout={signOut} />;
  }

  return <ChatApp key={user.id} user={user} onLogout={signOut} />;
}
