import { Compass, Upload, FileSearch, Table2, Bot, BarChart4 } from 'lucide-react';
import { TreeNavigator } from './TreeNavigator';

interface SidebarItem {
  label: string;
  id: string;
  icon: React.ReactNode;
}

const actionItems: SidebarItem[] = [
  { label: 'Carregar Dados', id: 'upload', icon: <Upload className="h-4 w-4" /> },
  { label: 'Revisar Schema', id: 'schema-review', icon: <FileSearch className="h-4 w-4" /> },
  { label: 'Minhas Tabelas', id: 'my-tables', icon: <Table2 className="h-4 w-4" /> },
  { label: 'Analise com IA', id: 'analysis-ai', icon: <Bot className="h-4 w-4" /> },
  { label: 'Dashboard com IA', id: 'dashboard-ia', icon: <BarChart4 className="h-4 w-4" /> },
];

interface SidebarProps {
  activeItem: string;
  onSelect: (id: string) => void;
  isExpanded: boolean;
}

export function Sidebar({ activeItem, onSelect, isExpanded }: SidebarProps) {
  return (
    <aside
      className={`sidebar ${isExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'} flex h-full shrink-0 flex-col border-r border-white/[0.06] bg-slate-950/80`}
    >
      {/* ── Navegar Section ── */}
      <div className="flex flex-col overflow-hidden px-2 pt-4">
        <div className="mb-2 flex items-center gap-2 px-2">
          <Compass className="h-4 w-4 shrink-0 text-sky-400/70" />
          {isExpanded && (
            <span className="sidebar-label text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Navegar
            </span>
          )}
        </div>

        {isExpanded && (
          <div className="sidebar-scroll max-h-[45vh] overflow-y-auto overflow-x-hidden">
            <TreeNavigator />
          </div>
        )}
      </div>

      {/* ── Divider ── */}
      <div className="mx-3 my-3 border-t border-white/[0.06]" />

      {/* ── Ações Section ── */}
      <div className="flex flex-1 flex-col overflow-hidden px-2">
        <nav className="space-y-1">
          {actionItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              title={item.label}
              className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium transition-all duration-150 ${
                activeItem === item.id
                  ? 'bg-violet-500/15 text-violet-300'
                  : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
              } ${!isExpanded ? 'justify-center px-0' : ''}`}
            >
              <span className="shrink-0">{item.icon}</span>
              {isExpanded && <span className="sidebar-label truncate">{item.label}</span>}
            </button>
          ))}
        </nav>
      </div>

      {/* Bottom spacer */}
      <div className="shrink-0 h-4" />
    </aside>
  );
}
