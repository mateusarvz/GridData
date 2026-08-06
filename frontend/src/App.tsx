import { useEffect, useState } from 'react';
import { LoginScreen } from './components/auth/LoginScreen';
import { ProfileCompletionScreen } from './components/auth/ProfileCompletionScreen';
import { AppShell } from './components/layout/AppShell';
import { DataUploadView } from './components/data-upload/DataUploadView';
import { MyTablesView } from './components/my-tables/MyTablesView';
import { SchemaReviewView } from './components/schema-review/SchemaReviewView';
import { AnalysisAIView } from './components/analysis-ai/AnalysisAIView';
import { DashboardIAView } from './components/analysis-ai/DashboardIAView';
import { clearSessionTables } from './services/dataUpload';
import {
  getSupabaseStatus,
  getGoogleSession,
  handleGoogleCallback,
  supabase,
} from './services/supabase';
import { useDataSessionStore } from './store/dataSessionStore';
import { useUserStore } from './store/userStore';
import { useWorkspaceStore } from './store/workspaceStore';
import { api } from './services/api';
import type { TabelaUploadada } from './types/schemaAnalysis';

function App() {
  const [supabaseStatus, setSupabaseStatus] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [profileEmail, setProfileEmail] = useState('');
  const [profileAuthUserId, setProfileAuthUserId] = useState<string | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('upload');
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
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

  // Detecta sessão do Google OAuth após redirect
  useEffect(() => {
    const checkGoogleSession = async () => {
      const session = await getGoogleSession();
      if (!session.ok || !session.accessToken) {
        setIsCheckingSession(false);
        return;
      }

      const result = await handleGoogleCallback(session.accessToken);
      if (!result.ok) {
        setIsCheckingSession(false);
        return;
      }

      if (result.userExists && result.user) {
        localStorage.setItem(
          'dama-box-auth',
          JSON.stringify({
            id: result.user.id,
            nome_usuario: result.user.nome_usuario,
            email: result.user.email,
            loggedIn: true,
            loggedAt: new Date().toISOString(),
          })
        );
        if (result.accessToken) {
          localStorage.setItem('damabox_token', result.accessToken);
        }
        handleLoginSuccess(result.user.nome_usuario, result.user.id, result.user.email);
      } else {
        handleProfileNeeded(session.email, session.authUserId);
      }
      setIsCheckingSession(false);
    };

    checkGoogleSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleProfileNeeded = (email: string, authUserId?: string) => {
    setProfileEmail(email);
    setProfileAuthUserId(authUserId);
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
    setProfileAuthUserId(undefined);
    setIsAuthenticated(true);
    initWorkspace(userId);
  };

  const handleCommitSuccess = async (_tabelas: string[]) => {
    await clearSessionTables();
    clearTables();
    setActiveTab('my-tables');
    resetSchemaState();
  };

  const handleLogout = async () => {
    try {
      await clearSessionTables();
    } catch {
      // Logout segue mesmo se limpeza falhar.
    }

    // Limpa a sessão do Supabase (Google OAuth)
    if (supabase) {
      await supabase.auth.signOut();
    }

    localStorage.removeItem('dama-box-auth');
    localStorage.removeItem('damabox_token');
    clearUser();
    clearTables();
    setIsAuthenticated(false);
    setNeedsProfile(false);
    setProfileEmail('');
    setProfileAuthUserId(undefined);
    setActiveTab('upload');
    resetSchemaState();
  };

  const resetSchemaState = () => {
    setSchemaFiles([]);
    setSchemaSessionId(null);
    setSchemaTabelasIniciais([]);
  };

  // Enquanto verifica a sessão do Google, não renderiza a tela de login
  if (isCheckingSession) {
    return (
      <div className="auth-bg flex min-h-screen items-center justify-center p-6">
        <div className="auth-grid fixed inset-0" />
        <div className="animate-fade-in relative z-10 flex flex-col items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-lg font-black text-white shadow-lg shadow-violet-500/25">
            D
          </div>
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-violet-500" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated && needsProfile) {
    return (
      <ProfileCompletionScreen
        email={profileEmail}
        authUserId={profileAuthUserId}
        onProfileComplete={handleProfileComplete}
      />
    );
  }

  if (!isAuthenticated) {
    return <LoginScreen onLogin={handleLoginSuccess} onNeedProfile={handleProfileNeeded} />;
  }

  const renderContent = () => {
    if (activeTab === 'my-tables') return <MyTablesView />;
    if (activeTab === 'analysis-ai') return <AnalysisAIView />;
    if (activeTab === 'dashboard-ia') return <DashboardIAView onDashboardGenerated={() => setSidebarExpanded(false)} />;
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
    return <DataUploadView onFilesLoaded={setSchemaFiles} onSessionCleared={resetSchemaState} />;
  };

  return (
    <>
      {supabaseStatus && (
        <div className="fixed right-4 top-4 z-50 rounded-2xl bg-slate-950/95 px-4 py-2 text-sm text-slate-100 shadow-lg shadow-black/30">
          {supabaseStatus}
        </div>
      )}
      <AppShell
        activeItem={activeTab}
        onSelect={setActiveTab}
        onLogout={handleLogout}
        sidebarExpanded={sidebarExpanded}
        onToggleSidebar={() => setSidebarExpanded((v) => !v)}
      >
        {renderContent()}
      </AppShell>
    </>
  );
}

export default App;
