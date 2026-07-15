import { useEffect, useState } from 'react';
import { LoginScreen } from './components/auth/LoginScreen';
import { ProfileCompletionScreen } from './components/auth/ProfileCompletionScreen';
import { AppShell } from './components/layout/AppShell';
import { DataUploadView } from './components/data-upload/DataUploadView';
import { GeminiChatView } from './components/gemini/GeminiChatView';
import { SchemaReviewView } from './components/schema-review/SchemaReviewView';
import { getSupabaseStatus } from './services/supabase';
import { useUserStore } from './store/userStore';
import type { TabelaUploadada } from './types/schemaAnalysis';

function App() {
  const [supabaseStatus, setSupabaseStatus] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [profileEmail, setProfileEmail] = useState('');
  const [activeTab, setActiveTab] = useState('upload');
  const [schemaSessionId, setSchemaSessionId] = useState<string | null>(null);
  const [schemaTabelasIniciais, setSchemaTabelasIniciais] = useState<TabelaUploadada[]>([]);
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

  const handleIrParaRevisao = (sessionId: string, tabelas: TabelaUploadada[]) => {
    setSchemaSessionId(sessionId);
    setSchemaTabelasIniciais(tabelas);
    setActiveTab('schema-review');
  };

  const handleCommitSuccess = (_tabelas: string[]) => {
    setActiveTab('upload');
    setSchemaSessionId(null);
    setSchemaTabelasIniciais([]);
  };

  if (!isAuthenticated && needsProfile) {
    return <ProfileCompletionScreen email={profileEmail} onProfileComplete={handleProfileComplete} />;
  }

  if (!isAuthenticated) {
    return <LoginScreen onLogin={handleLoginSuccess} onNeedProfile={handleProfileNeeded} />;
  }

  const renderContent = () => {
    if (activeTab === 'gemini') return <GeminiChatView />;
    if (activeTab === 'schema-review' && schemaSessionId) {
      return (
        <SchemaReviewView
          sessionId={schemaSessionId}
          tabelasIniciais={schemaTabelasIniciais}
          onVoltar={() => setActiveTab('upload')}
          onCommitSuccess={handleCommitSuccess}
        />
      );
    }
    return <DataUploadView onIrParaRevisao={handleIrParaRevisao} />;
  };

  return (
    <>
      {supabaseStatus && (
        <div className="fixed right-4 top-4 z-50 rounded-2xl bg-slate-950/95 px-4 py-2 text-sm text-slate-100 shadow-lg shadow-black/30">
          {supabaseStatus}
        </div>
      )}
      <AppShell activeItem={activeTab} onSelect={setActiveTab}>
        {renderContent()}
      </AppShell>
    </>
  );
}

export default App;

