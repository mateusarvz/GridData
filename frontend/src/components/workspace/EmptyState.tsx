import { FolderPlus, Table2 } from 'lucide-react';

interface EmptyStateProps {
  className?: string;
}

export function EmptyState({ className = '' }: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-24 px-8 ${className}`}
    >
      <div className="relative mb-6">
        {/* Dashed circle container */}
        <div
          className="w-24 h-24 rounded-full flex items-center justify-center"
          style={{
            border: '2px dashed var(--color-border)',
          }}
        >
          <div className="flex gap-2">
            <FolderPlus
              size={24}
              style={{ color: 'var(--color-muted)' }}
              strokeWidth={1.5}
            />
            <Table2
              size={24}
              style={{ color: 'var(--color-muted)' }}
              strokeWidth={1.5}
            />
          </div>
        </div>
      </div>

      <p
        className="text-base font-medium mb-2 text-balance text-center"
        style={{ color: 'var(--color-ink)' }}
      >
        Esta pasta está vazia
      </p>
      <p
        className="text-sm text-center max-w-xs"
        style={{ color: 'var(--color-muted)' }}
      >
        Arraste uma Pasta ou Tabela do menu inferior para começar a organizar
        seus dados, ou clique nos botões do dock.
      </p>
    </div>
  );
}
