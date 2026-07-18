import { useEffect, useState } from 'react';
import { Database, Table2 } from 'lucide-react';
import { listRelatedUserTables } from '../../services/dataUpload';
import { useUserStore } from '../../store/userStore';

export function MyTablesView() {
  const userId = useUserStore((state) => state.userId);
  const [tables, setTables] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!userId) return;

    let alive = true;
    setLoading(true);
    setError('');

    listRelatedUserTables(userId)
      .then((data) => {
        if (alive) setTables(data);
      })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : 'Erro ao carregar tabelas.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [userId]);

  return (
    <div className="flex h-full min-h-0 w-full flex-col rounded-[32px] border border-white/10 bg-slate-950/80 p-5 shadow-2xl shadow-slate-950/30 xl:p-6">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <Database className="h-4 w-4 text-violet-300" />
          Nomes de tabelas
        </div>
      </div>

      {loading && (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex items-center gap-3 text-sm text-slate-300">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
            Carregando tabelas...
          </div>
        </div>
      )}

      {error && <div className="m-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}

      {!loading && !error && (
        <div className="flex-1 overflow-y-auto p-4">
          {tables.length === 0 ? (
            <div className="flex min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.03] text-sm text-slate-400">
              Nenhuma tabela encontrada para este usuário.
            </div>
          ) : (
            <div className="grid gap-3">
              {tables.map((name, index) => (
                <div
                  key={`${name}-${index}`}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-gradient-to-r from-white/[0.05] to-white/[0.02] px-4 py-3 transition hover:border-violet-400/25 hover:bg-white/[0.08]"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300 ring-1 ring-violet-400/15">
                      <Table2 className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="truncate font-mono text-sm font-medium text-white">{name}</div>
                    </div>
                  </div>
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-500">
                    #{String(index + 1).padStart(2, '0')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
