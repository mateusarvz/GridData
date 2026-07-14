import type { ReactNode } from 'react';
import { Topbar } from './Topbar';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  activeItem: string;
  onSelect: (id: string) => void;
  children: ReactNode;
}

export function AppShell({ activeItem, onSelect, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Topbar />
      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 sm:px-6">
        <Sidebar activeItem={activeItem} onSelect={onSelect} />
        <main className="flex-1 rounded-[32px] border border-white/10 bg-slate-900/90 p-6 shadow-2xl shadow-slate-950/20">
          {children}
        </main>
      </div>
    </div>
  );
}
