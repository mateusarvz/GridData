import { useState } from 'react';
import { FolderPlus, Table2, Search } from 'lucide-react';
import { useDraggable } from '@dnd-kit/core';
import type { ItemType } from '../../types/workspace';

interface FloatingDockProps {
  onCreateClick: (type: ItemType) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

function DraggableDockItem({
  type,
  label,
  icon: Icon,
  onClick,
}: {
  type: ItemType;
  label: string;
  icon: typeof FolderPlus;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `dock-${type}`,
    data: { type: 'dock-create', itemType: type },
  });

  return (
    <button
      ref={setNodeRef}
      onClick={onClick}
      className="flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all duration-200 cursor-grab active:cursor-grabbing"
      style={{
        backgroundColor: isDragging ? 'var(--color-primary)' : 'transparent',
        color: isDragging ? 'white' : 'var(--color-ink)',
        opacity: isDragging ? 0.8 : 1,
      }}
      onMouseEnter={(e) => {
        if (!isDragging) {
          e.currentTarget.style.backgroundColor = 'var(--color-surface-hover)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isDragging) {
          e.currentTarget.style.backgroundColor = 'transparent';
        }
      }}
      aria-label={label}
      {...attributes}
      {...listeners}
    >
      <Icon size={16} strokeWidth={1.5} />
      <span>{label}</span>
    </button>
  );
}

export function FloatingDock({
  onCreateClick,
  searchQuery,
  onSearchChange,
}: FloatingDockProps) {
  const [searchExpanded, setSearchExpanded] = useState(false);

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-1 px-2 py-1.5 rounded-full"
      style={{
        zIndex: 'var(--z-dock)',
        backgroundColor: 'oklch(0.980 0.003 220 / 0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid oklch(0.900 0.005 220 / 0.6)',
        boxShadow: 'var(--shadow-dock)',
      }}
      role="toolbar"
      aria-label="Menu de ações rápidas"
    >
      <DraggableDockItem
        type="folder"
        label="Nova Pasta"
        icon={FolderPlus}
        onClick={() => onCreateClick('folder')}
      />

      <div
        className="w-px h-6 mx-1"
        style={{ backgroundColor: 'var(--color-border)' }}
        aria-hidden
      />

      <DraggableDockItem
        type="table"
        label="Nova Tabela"
        icon={Table2}
        onClick={() => onCreateClick('table')}
      />

      <div
        className="w-px h-6 mx-1"
        style={{ backgroundColor: 'var(--color-border)' }}
        aria-hidden
      />

      {/* Search */}
      <div className="flex items-center">
        {searchExpanded ? (
          <input
            autoFocus
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onBlur={() => {
              if (!searchQuery) setSearchExpanded(false);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                onSearchChange('');
                setSearchExpanded(false);
              }
            }}
            placeholder="Buscar..."
            className="w-36 px-3 py-1.5 rounded-full text-sm outline-none"
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-ink)',
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = 'var(--color-primary)')
            }
          />
        ) : (
          <button
            onClick={() => setSearchExpanded(true)}
            className="p-2.5 rounded-full transition-colors duration-150 cursor-pointer"
            style={{ color: 'var(--color-muted)' }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.backgroundColor =
                'var(--color-surface-hover)')
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.backgroundColor = 'transparent')
            }
            aria-label="Buscar"
          >
            <Search size={16} strokeWidth={1.5} />
          </button>
        )}
      </div>
    </div>
  );
}
