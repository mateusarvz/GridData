import type { UploadedTableMeta, RelatedUserTable } from '../../types/dataUpload';

interface LoadedTablesPanelProps {
  tables: UploadedTableMeta[];
  relatedTables: RelatedUserTable[];
  onSelectTable: (tableId: string) => void;
}

export function LoadedTablesPanel({ tables, relatedTables, onSelectTable }: LoadedTablesPanelProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <h3 className="text-base font-semibold text-white">Tabelas carregadas</h3>
        <p className="mt-1 text-sm text-slate-400">Clique em uma tabela para ver os dados temporários carregados na sessão.</p>
      </div>

      <div className="rounded-[28px] border border-cyan-400/20 bg-cyan-500/5 p-5">
        <h3 className="text-base font-semibold text-cyan-100">Tabelas do usuário logado</h3>
        <p className="mt-1 text-sm text-cyan-100/70">
          Catálogo vindo do Supabase com base em `users`, `user_subscriptions`, `user_tables`,
          `user_table_columns`, `user_table_relationships`, `file_uploads`, `billing_transactions` e `audit_logs`.
        </p>
        <div className="mt-4 grid gap-3">
          {relatedTables.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-slate-400">
              Nenhuma tabela relacionada encontrada para este usuário.
            </div>
          ) : (
            relatedTables.map((table) => (
              <div
                key={`${table.table_name}-${table.display_name}-${table.category}`}
                className="rounded-2xl border border-white/10 bg-slate-950/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">{table.display_name}</div>
                    <div className="text-xs uppercase tracking-[0.18em] text-cyan-200/80">{table.category}</div>
                  </div>
                  <span className="rounded-full bg-cyan-500/15 px-3 py-1 text-xs text-cyan-100">
                    {table.table_name}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
                  {typeof table.row_count === 'number' && <span>Linhas: {table.row_count}</span>}
                  {typeof table.columns_count === 'number' && <span>Colunas: {table.columns_count}</span>}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="grid gap-4">
        {tables.map((table) => (
          <button
            key={table.table_id}
            type="button"
            onClick={() => onSelectTable(table.table_id)}
            className="w-full rounded-[24px] border border-white/10 bg-slate-900/80 p-5 text-left transition hover:border-violet-400/50 hover:bg-slate-900"
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <h4 className="text-base font-semibold text-white">{table.file_name}</h4>
                <p className="mt-1 text-sm text-slate-400">
                  {table.columns.length} colunas · {table.row_count} linhas
                </p>
              </div>
              <span className="rounded-full bg-violet-500/20 px-3 py-1 text-xs uppercase tracking-[0.2em] text-violet-200">
                {table.table_id.slice(0, 5)}...
              </span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
