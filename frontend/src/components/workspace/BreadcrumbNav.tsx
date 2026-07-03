import { ChevronRight, Home } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspaceStore';

export function BreadcrumbNav() {
  const breadcrumb = useWorkspaceStore((s) => s.breadcrumb);
  const navigateTo = useWorkspaceStore((s) => s.navigateTo);

  return (
    <nav aria-label="Navegação do workspace" className="flex items-center gap-0.5 px-1 py-2 overflow-x-auto">
      {breadcrumb.map((crumb, i) => (
        <div key={crumb.id ?? 'root'} className="flex items-center gap-0.5">
          {i > 0 && (
            <ChevronRight size={14} style={{ color: 'var(--color-muted)' }} strokeWidth={2} aria-hidden />
          )}
          <button
            onClick={() => navigateTo(crumb.id)}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-sm transition-colors duration-150 cursor-pointer"
            style={{
              color: i === breadcrumb.length - 1 ? 'var(--color-ink)' : 'var(--color-muted)',
              fontWeight: i === breadcrumb.length - 1 ? 600 : 400,
            }}
            onMouseEnter={(e) => {
              if (i < breadcrumb.length - 1)
                e.currentTarget.style.backgroundColor = 'var(--color-surface)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
            aria-current={i === breadcrumb.length - 1 ? 'page' : undefined}
          >
            {crumb.id === null && <Home size={14} strokeWidth={2} />}
            <span>{crumb.name}</span>
          </button>
        </div>
      ))}
    </nav>
  );
}
