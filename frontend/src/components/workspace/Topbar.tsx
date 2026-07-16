import React, { useEffect } from 'react';
import { Box, Search, Wifi, WifiOff, Bell, User, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspaceStore';

export const Topbar: React.FC = () => {
  const { isOnline, checkApiStatus } = useWorkspaceStore();
  const [checking, setChecking] = React.useState(false);

  useEffect(() => {
    checkApiStatus();
    // Verificar conexão periodicamente a cada 30s
    const timer = setInterval(() => checkApiStatus(), 30000);
    return () => clearInterval(timer);
  }, [checkApiStatus]);

  const handleManualCheck = async () => {
    setChecking(true);
    await checkApiStatus();
    setTimeout(() => setChecking(false), 500);
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50 glass-dock px-6 flex items-center justify-between border-b border-[var(--color-border)] shadow-sm animate-fade-in">
      {/* Lado Esquerdo: Identidade Visual e Logo */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-accent)] flex items-center justify-center text-white shadow-md">
          <Box className="w-6 h-6 animate-pulse-glow" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-accent)] bg-clip-text text-transparent">
            Dama Box
          </span>
          <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
            Enterprise 2.0
          </span>
        </div>
      </div>

      {/* Centro: Busca Rápida */}
      <div className="hidden md:flex items-center w-96 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-muted)]" />
          <input
            type="text"
            placeholder="Buscar Workspaces, Tabelas ou Colunas... (Ctrl + K)"
            className="w-full pl-9 pr-4 py-2 text-sm rounded-xl bg-black/5 border border-[var(--color-border)] focus:outline-none focus:border-[var(--color-primary)] focus:bg-white transition-all placeholder-[var(--color-muted)]"
          />
        </div>
      </div>

      {/* Lado Direito: Status API, Tenant e Usuário */}
      <div className="flex items-center gap-4">
        {/* Indicador do Status da API */}
        <button
          onClick={handleManualCheck}
          title="Clique para testar conexão com o Backend FastAPI"
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
            isOnline
              ? 'bg-[var(--color-success-soft)] text-emerald-800 border-emerald-300 hover:bg-emerald-100'
              : 'bg-[var(--color-warning-soft)] text-amber-800 border-amber-300 hover:bg-amber-100'
          }`}
        >
          {checking ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : isOnline ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-600" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-amber-600" />
          )}
          <span>{isOnline ? 'API Conectada' : 'Modo Demo / Offline'}</span>
        </button>

        {/* Badge do Tenant Ativo */}
        <div className="hidden sm:flex items-center gap-2 text-xs text-[var(--color-muted)] bg-[var(--color-surface)] px-3 py-1.5 rounded-lg border border-[var(--color-border)]">
          <span className="w-2 h-2 rounded-full bg-[var(--color-primary)]"></span>
          <span className="font-medium text-[var(--color-ink)]">empresa_dama</span>
        </div>

        {/* Notificações */}
        <button className="p-2 rounded-xl hover:bg-[var(--color-surface-hover)] transition-colors relative text-[var(--color-muted)] hover:text-[var(--color-ink)]">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[var(--color-accent)] rounded-full"></span>
        </button>

        {/* Perfil / Avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-[var(--color-border)]">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-600 flex items-center justify-center text-white font-medium text-sm shadow-sm ring-2 ring-white">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-bold leading-none text-[var(--color-ink)]">Admin Dama</div>
            <div className="text-[10px] text-[var(--color-muted)] mt-0.5">Owner · RBAC</div>
          </div>
        </div>
      </div>
    </header>
  );
};
