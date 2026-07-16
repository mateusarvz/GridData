import { useState } from 'react';
import { Folder, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { useDroppable } from '@dnd-kit/core';
import type { FolderItem, FolderCounts } from '../../types/workspace';

interface FolderCardProps {
  item: FolderItem;
  counts: FolderCounts;
  onOpen: () => void;
  onRename: (name: string) => void;
  onDelete: () => void;
  style?: React.CSSProperties;
  dragListeners?: Record<string, unknown>;
  dragAttributes?: Record<string, unknown>;
  isDragging?: boolean;
}

export function FolderCard({
  item, counts, onOpen, onRename, onDelete,
  style, dragListeners, dragAttributes, isDragging,
}: FolderCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(item.name);

  const { setNodeRef, isOver } = useDroppable({
    id: `folder-drop-${item.id}`,
    data: { type: 'folder-target', folderId: item.id },
  });

  const handleRenameSubmit = () => {
    const t = renameValue.trim();
    if (t && t !== item.name) onRename(t);
    else setRenameValue(item.name);
    setIsRenaming(false);
  };

  const countText = [
    counts.folders > 0 ? `${counts.folders} pasta${counts.folders > 1 ? 's' : ''}` : '',
    counts.tables > 0 ? `${counts.tables} tabela${counts.tables > 1 ? 's' : ''}` : '',
  ].filter(Boolean).join(', ') || 'Vazia';

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        opacity: isDragging ? 0.3 : 1,
        backgroundColor: isOver ? 'var(--color-primary-soft)' : 'var(--color-bg)',
        border: isOver ? '2px dashed var(--color-primary)' : '1px solid var(--color-border)',
        boxShadow: isOver ? 'none' : 'var(--shadow-sm)',
        cursor: 'default',
      }}
      className="rounded-xl p-4 transition-all duration-200 group w-[240px] select-none"
      tabIndex={0}
      aria-label={`Pasta ${item.name}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onOpen();
        if (e.key === 'F2') { e.preventDefault(); setIsRenaming(true); }
        if (e.key === 'Delete') { e.preventDefault(); onDelete(); }
      }}
      onMouseEnter={(e) => {
        if (!isOver) {
          e.currentTarget.style.boxShadow = 'var(--shadow-md)';
          e.currentTarget.style.borderColor = 'var(--color-border-hover)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isOver) {
          e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
          e.currentTarget.style.borderColor = 'var(--color-border)';
        }
      }}
    >
      <div className="flex items-start justify-between mb-3">
        {/* Drag handle — the folder icon area */}
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center cursor-grab active:cursor-grabbing"
          style={{ backgroundColor: 'var(--color-primary-soft)' }}
          {...dragAttributes}
          {...dragListeners}
          title="Arraste para mover"
        >
          <Folder size={20} style={{ color: 'var(--color-primary)' }} strokeWidth={1.5} />
        </div>

        <div className="relative flex items-center gap-1">
          {/* Open folder button */}
          <button
            onClick={onOpen}
            className="px-2 py-1 rounded-md text-xs font-medium transition-colors duration-150 cursor-pointer opacity-0 group-hover:opacity-100"
            style={{ color: 'var(--color-primary)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-primary-soft)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            title="Abrir pasta"
          >
            Abrir →
          </button>

          <button
            onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
            className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity duration-150 cursor-pointer"
            style={{ color: 'var(--color-muted)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-surface)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            aria-label="Ações da pasta"
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

      <p className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>{countText}</p>

      {isOver && (
        <p className="text-xs mt-2 font-medium" style={{ color: 'var(--color-primary)' }}>
          Solte aqui para mover para dentro
        </p>
      )}
    </div>
  );
}
