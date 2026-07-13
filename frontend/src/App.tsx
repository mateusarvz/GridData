import { useEffect, useState } from 'react';
import { LoginScreen } from './components/auth/LoginScreen';
import { WorkspaceCanvas } from './components/workspace/WorkspaceCanvas';
import { getSupabaseStatus } from './services/supabase';

function App() {
  const [supabaseStatus, setSupabaseStatus] = useState('Conectando ao Supabase...');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userName, setUserName] = useState('');
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const stored = localStorage.getItem('dama-box-auth');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed?.loggedIn) {
        setIsAuthenticated(true);
        setUserName(parsed.name || 'Usuário');
        setUserId(parsed.id || '');
      }
    }

    getSupabaseStatus().then((status) => {
      setSupabaseStatus(status.ok ? 'Supabase conectado' : `Supabase indisponível: ${status.error}`);
    });
  }, []);

  const handleLogin = (name: string, id: string) => {
    setUserName(name);
    setUserId(id);
    setIsAuthenticated(true);
  };

  if (!isAuthenticated) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <>
      <div
        style={{
          position: 'fixed',
          top: 12,
          right: 12,
          zIndex: 999,
          padding: '8px 12px',
          borderRadius: 999,
          background: 'rgba(15, 23, 42, 0.9)',
          color: '#f8fafc',
          fontSize: '12px',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.2)',
        }}
      >
        {supabaseStatus} · {userName} · ID: {userId || 'sem id'}
      </div>
      <WorkspaceCanvas />
    </>
  );
}

export default App;
