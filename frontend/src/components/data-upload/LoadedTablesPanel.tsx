import type { UploadedTableMeta } from '../../types/dataUpload';

interface LoadedTablesPanelProps {
  tables: UploadedTableMeta[];
  onSelectTable: (tableId: string) => void;
}

export function LoadedTablesPanel({ tables, onSelectTable }: LoadedTablesPanelProps) {
  return (
    <section className="space-y-4">
      <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
        <h3 className="text-base font-semibold text-white">Tabelas carregadas</h3>
        <p className="mt-1 text-sm text-slate-400">Clique em uma tabela para ver os dados temporários carregados na sessão.</p>
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
                <p className="mt-1 text-sm text-slate-400">{table.columns.length} colunas · {table.row_count} linhas</p>
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
