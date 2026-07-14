interface SidebarItem {
  label: string;
  id: string;
}

const items: SidebarItem[] = [
  { label: 'Carregar Dados', id: 'upload' },
  { label: 'Conversar com Gemini', id: 'gemini' },
];

interface SidebarProps {
  activeItem: string;
  onSelect: (id: string) => void;
}

export function Sidebar({ activeItem, onSelect }: SidebarProps) {
  return (
    <aside className="sticky top-16 z-30 h-[calc(100vh-4rem)] w-full max-w-[260px] border-r border-white/10 bg-slate-950/90 p-4 text-slate-100 shadow-xl shadow-slate-950/20">
      <div className="mb-10 text-sm uppercase tracking-[0.25em] text-violet-300">Ações</div>
      <nav className="space-y-2">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
            className={`w-full rounded-2xl px-4 py-3 text-left text-sm font-medium transition ${
              activeItem === item.id ? 'bg-violet-500/20 text-white' : 'text-slate-300 hover:bg-white/5'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
