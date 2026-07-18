import { useState, type ReactNode } from 'react';
import { PanelLeftClose, PanelLeft } from 'lucide-react';
import { Topbar } from './Topbar';
import { Sidebar } from './Sidebar';
import { GeminiSidebar } from '../gemini/GeminiSidebar';

interface AppShellProps {
  activeItem: string;
  onSelect: (id: string) => void;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({ activeItem, onSelect, onLogout, children }: AppShellProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-slate-950 text-white">
      <Topbar onLogout={onLogout} />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Sidebar toggle + sidebar */}
        <div className="relative flex h-full shrink-0">
          {/* Toggle button */}
          <button
            type="button"
            onClick={() => setSidebarExpanded((v) => !v)}
            className="absolute -right-3 top-5 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-slate-900 text-slate-400 shadow-lg transition-colors hover:bg-slate-800 hover:text-slate-200"
            title={sidebarExpanded ? 'Recolher menu' : 'Expandir menu'}
          >
            {sidebarExpanded ? (
              <PanelLeftClose className="h-3 w-3" />
            ) : (
              <PanelLeft className="h-3 w-3" />
            )}
          </button>

          <Sidebar activeItem={activeItem} onSelect={onSelect} isExpanded={sidebarExpanded} />
        </div>

        {/* Main content */}
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-4 xl:p-5">
          <div className="flex min-h-0 flex-1 overflow-hidden rounded-2xl border border-white/[0.06] bg-slate-900/60 p-4 shadow-xl shadow-black/10 xl:rounded-3xl xl:p-6">
            {children}
          </div>
        </main>

        <GeminiSidebar />
      </div>
    </div>
  );
}
