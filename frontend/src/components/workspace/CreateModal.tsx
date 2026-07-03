import { useState, useRef, useEffect } from 'react';
import { X } from 'lucide-react';
import type { ItemType } from '../../types/workspace';

interface CreateModalProps {
  type: ItemType;
  onConfirm: (name: string) => void;
  onClose: () => void;
}

export function CreateModal({ type, onConfirm, onClose }: CreateModalProps) {
  const [name, setName] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) {
      onConfirm(trimmed);
      onClose();
    }
  };

  const label = type === 'folder' ? 'Nova Pasta' : 'Nova Tabela';

  return (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{
        zIndex: 'var(--z-modal-backdrop)',
        backgroundColor: 'oklch(0.200 0.000 0 / 0.3)',
      }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      <div
        className="rounded-xl p-6 w-full max-w-sm shadow-lg transition-transform duration-200"
        style={{
          backgroundColor: 'var(--color-bg)',
          border: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-lg)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-base font-semibold"
            style={{ color: 'var(--color-ink)' }}
          >
            {label}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md transition-colors duration-150 cursor-pointer"
            style={{ color: 'var(--color-muted)' }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.backgroundColor =
                'var(--color-surface-hover)')
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.backgroundColor = 'transparent')
            }
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={
              type === 'folder'
                ? 'Nome da pasta...'
                : 'Nome da tabela...'
            }
            className="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-150"
            style={{
              backgroundColor: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-ink)',
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = 'var(--color-primary)')
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = 'var(--color-border)')
            }
          />

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 cursor-pointer"
              style={{
                color: 'var(--color-muted)',
                backgroundColor: 'transparent',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.backgroundColor =
                  'var(--color-surface)')
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor = 'transparent')
              }
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                backgroundColor: 'var(--color-primary)',
                color: 'white',
              }}
              onMouseEnter={(e) => {
                if (!e.currentTarget.disabled)
                  e.currentTarget.style.backgroundColor =
                    'var(--color-primary-hover)';
              }}
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor =
                  'var(--color-primary)')
              }
            >
              Criar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
