import { useState } from 'react';
import { Table2, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import type { TableItem } from '../../types/workspace';

interface TableCardProps {
  item: TableItem;
  onOpen: () => void;
  onRename: (name: string) => void;
  onDelete: () => void;
  style?: React.CSSProperties;
  dragListeners?: Record<string, unknown>;
  dragAttributes?: Record<string, unknown>;
  isDragging?: boolean;
}

export function TableCard({ item, onOpen, onRename, onDelete, style, dragListeners, dragAttributes, isDragging }: TableCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(item.name);

  const handleRenameSubmit = () => {
    const t = renameValue.trim();
    if (t && t !== item.name) onRename(t);
    else setRenameValue(item.name);
    setIsRenaming(false);
  };

  return (
    <div
      style={{
        ...style,
        opacity: isDragging ? 0.3 : 1,
        backgroundColor: 'var(--color-bg)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
        cursor: 'default',
      }}
      className="rounded-xl p-4 transition-all duration-200 group w-[240px] select-none"
      tabIndex={0}
      aria-label={`Tabela ${item.name}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onOpen();
        if (e.key === 'F2') { e.preventDefault(); setIsRenaming(true); }
        if (e.key === 'Delete') { e.preventDefault(); onDelete(); }
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.borderColor = 'var(--color-border-hover)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        e.currentTarget.style.borderColor = 'var(--color-border)';
      }}
    >
      <div className="flex items-start justify-between mb-3">
        {/* Drag handle — icon area */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center cursor-grab active:cursor-grabbing"
          style={{ backgroundColor: 'var(--color-accent-soft)' }}
          {...dragAttributes}
          {...dragListeners}
          title="Arraste para mover"
        >
          <Table2 size={20} style={{ color: 'var(--color-accent)' }} strokeWidth={1.5} />
        </div>

        <div className="relative flex items-center gap-1">
          <button
            onClick={onOpen}
            className="px-2 py-1 rounded-md text-xs font-medium transition-colors duration-150 cursor-pointer opacity-0 group-hover:opacity-100"
            style={{ color: 'var(--color-accent)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-accent-soft)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            title="Ver tabela"
          >
            Ver →
          </button>

          <button
            onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
            className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-150 cursor-pointer"
            style={{ color: 'var(--color-muted)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-surface)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            aria-label="Ações da tabela"
          >
            <MoreHorizontal size={16} />
          </button>

          {menuOpen && (
            <div
              className="absolute right-0 top-8 rounded-lg py-1 min-w-[140px]"
              style={{
                backgroundColor: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 'var(--z-dropdown)' as React.CSSProperties['zIndex'],
              }}
              onMouseLeave={() => setMenuOpen(false)}
            >
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); setIsRenaming(true); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left transition-colors duration-150 cursor-pointer"
                style={{ color: 'var(--color-ink)' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-surface)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <Pencil size={14} /> Renomear
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onDelete(); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left transition-colors duration-150 cursor-pointer"
                style={{ color: 'var(--color-error)' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-error-soft)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <Trash2 size={14} /> Excluir
              </button>
            </div>
          )}
        </div>
      </div>

      {isRenaming ? (
        <input
          autoFocus
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onBlur={handleRenameSubmit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleRenameSubmit();
            if (e.key === 'Escape') { setRenameValue(item.name); setIsRenaming(false); }
            e.stopPropagation();
          }}
          onClick={(e) => e.stopPropagation()}
          className="w-full px-2 py-1 rounded-md text-sm font-semibold outline-none"
          style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-primary)', color: 'var(--color-ink)' }}
        />
      ) : (
        <h3 className="text-sm font-semibold mb-1 truncate" style={{ color: 'var(--color-ink)' }}>
          {item.name}
        </h3>
      )}

      <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>
        {item.description || 'Vazia · 0 colunas'}
      </p>
    </div>
  );
}
