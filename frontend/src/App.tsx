import { useEffect, useState } from 'react';
import { LoginScreen } from './components/auth/LoginScreen';
import { ProfileCompletionScreen } from './components/auth/ProfileCompletionScreen';
import { AppShell } from './components/layout/AppShell';
import { DataUploadView } from './components/data-upload/DataUploadView';
import { getSupabaseStatus } from './services/supabase';
import { useUserStore } from './store/userStore';

function App() {
  const [supabaseStatus, setSupabaseStatus] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [profileEmail, setProfileEmail] = useState('');
  const setUser = useUserStore((state) => state.setUser);

  useEffect(() => {
    getSupabaseStatus().then((status) => {
      setSupabaseStatus(status.ok ? '' : `Supabase indisponível: ${status.error}`);
    });
  }, []);

  const handleProfileNeeded = (email: string) => {
    setProfileEmail(email);
    setNeedsProfile(true);
  };

  const handleLoginSuccess = (nomeUsuario: string, userId: string, email: string) => {
    setUser(userId, nomeUsuario, email);
    setNeedsProfile(false);
    setIsAuthenticated(true);
  };

  const handleProfileComplete = (nomeUsuario: string, userId: string) => {
    setUser(userId, nomeUsuario, profileEmail);
    setNeedsProfile(false);
    setIsAuthenticated(true);
  };

  if (!isAuthenticated && needsProfile) {
    return <ProfileCompletionScreen email={profileEmail} onProfileComplete={handleProfileComplete} />;
  }

  if (!isAuthenticated) {
    return <LoginScreen onLogin={handleLoginSuccess} onNeedProfile={handleProfileNeeded} />;
  }

  return (
    <>
      {supabaseStatus && (
        <div className="fixed right-4 top-4 z-50 rounded-2xl bg-slate-950/95 px-4 py-2 text-sm text-slate-100 shadow-lg shadow-black/30">
          {supabaseStatus}
        </div>
      )}
      <AppShell activeItem="upload" onSelect={() => null}>
        <DataUploadView />
      </AppShell>
    </>
  );
}

export default App;
