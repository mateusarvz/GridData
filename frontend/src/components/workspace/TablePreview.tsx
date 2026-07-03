import { X, Table2, Columns3 } from 'lucide-react';
import { useEffect } from 'react';
import type { TableItem } from '../../types/workspace';

interface TablePreviewProps {
  item: TableItem;
  onClose: () => void;
}

export function TablePreview({ item, onClose }: TablePreviewProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed top-0 right-0 h-full w-full max-w-sm"
      style={{
        zIndex: 'var(--z-modal)',
        backgroundColor: 'var(--color-bg)',
        borderLeft: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-lg)',
      }}
      role="dialog"
      aria-label={`Pré-visualização: ${item.name}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: 'var(--color-accent-soft)' }}
          >
            <Table2
              size={16}
              style={{ color: 'var(--color-accent)' }}
              strokeWidth={1.5}
            />
          </div>
          <h2
            className="text-base font-semibold truncate"
            style={{ color: 'var(--color-ink)' }}
          >
            {item.name}
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-md transition-colors duration-150 cursor-pointer"
          style={{ color: 'var(--color-muted)' }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.backgroundColor = 'var(--color-surface)')
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.backgroundColor = 'transparent')
          }
          aria-label="Fechar"
        >
          <X size={18} />
        </button>
      </div>

      {/* Body */}
      <div className="px-5 py-5 space-y-5">
        {/* Status */}
        <div>
          <p
            className="text-xs font-medium uppercase tracking-wide mb-2"
            style={{ color: 'var(--color-muted)' }}
          >
            Status
          </p>
          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
            style={{
              backgroundColor:
                item.columnCount > 0
                  ? 'var(--color-success-soft)'
                  : 'var(--color-surface)',
              color:
                item.columnCount > 0
                  ? 'var(--color-success)'
                  : 'var(--color-muted)',
            }}
          >
            <Columns3 size={12} />
            {item.columnCount > 0
              ? `${item.columnCount} coluna${item.columnCount > 1 ? 's' : ''} definida${item.columnCount > 1 ? 's' : ''}`
              : 'Nenhuma coluna definida'}
          </div>
        </div>

        {/* Details */}
        <div>
          <p
            className="text-xs font-medium uppercase tracking-wide mb-2"
            style={{ color: 'var(--color-muted)' }}
          >
            Detalhes
          </p>
          <dl className="space-y-2">
            <div className="flex justify-between text-sm">
              <dt style={{ color: 'var(--color-muted)' }}>Criada em</dt>
              <dd style={{ color: 'var(--color-ink)' }}>
                {item.createdAt.toLocaleDateString('pt-BR')}
              </dd>
            </div>
            <div className="flex justify-between text-sm">
              <dt style={{ color: 'var(--color-muted)' }}>Atualizada em</dt>
              <dd style={{ color: 'var(--color-ink)' }}>
                {item.updatedAt.toLocaleDateString('pt-BR')}
              </dd>
            </div>
          </dl>
        </div>

        {/* Coming soon */}
        <div
          className="rounded-lg p-4 text-center"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px dashed var(--color-border)',
          }}
        >
          <p
            className="text-sm font-medium mb-1"
            style={{ color: 'var(--color-ink)' }}
          >
            Editor de Colunas
          </p>
          <p
            className="text-xs"
            style={{ color: 'var(--color-muted)' }}
          >
            A modelagem visual de colunas será conectada na próxima fase.
          </p>
        </div>
      </div>
    </div>
  );
}
