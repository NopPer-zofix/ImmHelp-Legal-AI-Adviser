import { useState } from 'react';
import AuthPage from './components/AuthPage';
import ChatApp from './components/ChatApp';
import { session } from './lib/storage';

export default function App() {
  // Remembered across refreshes — Streamlit logged you out on every reload
  const [user, setUser] = useState(session.load);

  const signIn = (u) => {
    session.save(u);
    setUser(u);
  };

  const signOut = () => {
    session.clear();
    window.history.replaceState(null, '', window.location.pathname);
    setUser(null);
  };

  return user ? <ChatApp key={user.id} user={user} onLogout={signOut} /> : <AuthPage onAuth={signIn} />;
}
