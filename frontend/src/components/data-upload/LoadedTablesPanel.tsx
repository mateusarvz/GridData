import type { UploadedTableMeta } from '../../types/dataUpload';

interface LoadedTablesPanelProps {
  tables: UploadedTableMeta[];
  onSelectTable: (tableId: string) => void;
}

export function LoadedTablesPanel({ tables, onSelectTable }: LoadedTablesPanelProps) {
  return (
    <section className="flex min-h-0 w-full flex-col gap-4 overflow-hidden">
      <div className="shrink-0 w-full rounded-[28px] border border-white/10 bg-white/5 p-4">
        <h3 className="text-base font-semibold text-white">Tabelas carregadas</h3>
        <p className="mt-1 text-sm text-slate-400">
          Clique em uma tabela para ver os dados temporários carregados na sessão.
        </p>
      </div>

      <div className="grid min-h-0 w-full gap-4 overflow-y-auto pr-1">
        {tables.length === 0 ? (
          <div className="w-full rounded-[24px] border border-dashed border-white/10 bg-slate-950/60 p-4 text-sm text-slate-400">
            Nenhum DataFrame carregado na sessão.
          </div>
        ) : (
          tables.map((table) => (
            <button
              key={table.table_id}
              type="button"
              onClick={() => onSelectTable(table.table_id)}
              className="w-full rounded-[24px] border border-white/10 bg-slate-900/80 p-4 text-left transition hover:border-violet-400/50 hover:bg-slate-900"
            >
              <div className="flex w-full items-center justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h4 className="truncate text-base font-semibold text-white">{table.file_name}</h4>
                  <p className="mt-1 truncate text-sm text-slate-400">
                    {table.columns.length} colunas · {table.row_count} linhas
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-violet-500/20 px-3 py-1 text-xs uppercase tracking-[0.2em] text-violet-200">
                  {table.table_id.slice(0, 5)}...
                </span>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
