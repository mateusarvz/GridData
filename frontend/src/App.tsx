import { useEffect, useState } from 'react';
import { LoginScreen } from './components/auth/LoginScreen';
import { ProfileCompletionScreen } from './components/auth/ProfileCompletionScreen';
import { AppShell } from './components/layout/AppShell';
import { DataUploadView } from './components/data-upload/DataUploadView';
import { MyTablesView } from './components/my-tables/MyTablesView';
import { SchemaReviewView } from './components/schema-review/SchemaReviewView';
import { clearSessionTables } from './services/dataUpload';
import { getSupabaseStatus } from './services/supabase';
import { useDataSessionStore } from './store/dataSessionStore';
import { useUserStore } from './store/userStore';
import { useWorkspaceStore } from './store/workspaceStore';
import { api } from './services/api';
import type { TabelaUploadada } from './types/schemaAnalysis';

function App() {
  const [supabaseStatus, setSupabaseStatus] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [profileEmail, setProfileEmail] = useState('');
  const [activeTab, setActiveTab] = useState('upload');
  const [schemaFiles, setSchemaFiles] = useState<File[]>([]);
  const [schemaSessionId, setSchemaSessionId] = useState<string | null>(null);
  const [schemaTabelasIniciais, setSchemaTabelasIniciais] = useState<TabelaUploadada[]>([]);
  const setUser = useUserStore((state) => state.setUser);
  const clearUser = useUserStore((state) => state.clearUser);
  const clearTables = useDataSessionStore((state) => state.clearTables);
  const fetchTree = useWorkspaceStore((state) => state.fetchTree);
  const checkApiStatus = useWorkspaceStore((state) => state.checkApiStatus);

  useEffect(() => {
    getSupabaseStatus().then((status) => {
      setSupabaseStatus(status.ok ? '' : `Supabase indisponível: ${status.error}`);
    });
  }, []);

  // After login, initialize workspace
  const initWorkspace = async (userId: string) => {
    await checkApiStatus();
    if (!api.isOnline) return;

    // List user's workspaces
    const workspaces = await api.listWorkspaces();
    if (workspaces.length > 0) {
      // Use the first workspace
      await fetchTree(workspaces[0].id);
    } else {
      // Create a default workspace for the user
      const newWs = await api.createWorkspace('Meu Workspace', userId);
      if (newWs) {
        await fetchTree(newWs.id);
      }
    }
  };

  const handleProfileNeeded = (email: string) => {
    setProfileEmail(email);
    setNeedsProfile(true);
  };

  const handleLoginSuccess = (nomeUsuario: string, userId: string, email: string) => {
    clearSessionTables().catch(() => {});
    setUser(userId, nomeUsuario, email);
    setNeedsProfile(false);
    setIsAuthenticated(true);
    initWorkspace(userId);
  };

  const handleProfileComplete = (nomeUsuario: string, userId: string) => {
    clearSessionTables().catch(() => {});
    setUser(userId, nomeUsuario, profileEmail);
    setNeedsProfile(false);
    setIsAuthenticated(true);
    initWorkspace(userId);
  };

  const handleCommitSuccess = async (_tabelas: string[]) => {
    await clearSessionTables();
    clearTables();
    setActiveTab('upload');
    setSchemaFiles([]);
    setSchemaSessionId(null);
    setSchemaTabelasIniciais([]);
  };

  const handleLogout = async () => {
    try {
      await clearSessionTables();
    } catch {
      // Logout segue mesmo se limpeza falhar.
    }

    localStorage.removeItem('dama-box-auth');
    clearUser();
    clearTables();
    setIsAuthenticated(false);
    setNeedsProfile(false);
    setProfileEmail('');
    setActiveTab('upload');
    setSchemaFiles([]);
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
    if (activeTab === 'my-tables') return <MyTablesView />;
    if (activeTab === 'schema-review') {
      return (
        <div className="h-full min-h-0 w-full overflow-y-auto">
          <SchemaReviewView
            sessionId={schemaSessionId}
            tabelasIniciais={schemaTabelasIniciais}
            arquivosCarregados={schemaFiles}
            onVoltar={() => setActiveTab('upload')}
            onCommitSuccess={handleCommitSuccess}
            onSchemaReady={(sessionId, tabelas) => {
              setSchemaSessionId(sessionId);
              setSchemaTabelasIniciais(tabelas);
            }}
          />
        </div>
      );
    }
    return <DataUploadView onFilesLoaded={setSchemaFiles} />;
  };

  return (
    <>
      {supabaseStatus && (
        <div className="fixed right-4 top-4 z-50 rounded-2xl bg-slate-950/95 px-4 py-2 text-sm text-slate-100 shadow-lg shadow-black/30">
          {supabaseStatus}
        </div>
      )}
      <AppShell activeItem={activeTab} onSelect={setActiveTab} onLogout={handleLogout}>
        {renderContent()}
      </AppShell>
    </>
  );
}

export default App;
