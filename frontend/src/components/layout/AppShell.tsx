import type { ReactNode } from 'react';
import { Topbar } from './Topbar';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  activeItem: string;
  onSelect: (id: string) => void;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({ activeItem, onSelect, onLogout, children }: AppShellProps) {
  return (
    <div className="h-screen overflow-hidden bg-slate-950 text-white">
      <Topbar onLogout={onLogout} />
      <div className="flex h-[calc(100vh-4rem)] w-full gap-6 overflow-hidden px-8 py-6">
        <Sidebar activeItem={activeItem} onSelect={onSelect} />
        <main className="flex min-h-0 flex-1 overflow-hidden rounded-[32px] border border-white/10 bg-slate-900/90 p-4 shadow-2xl shadow-slate-950/20 xl:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
