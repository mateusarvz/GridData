import type { TablePreviewResponse } from '../../types/dataUpload';

interface TablePreviewProps {
  table: TablePreviewResponse;
}

export function TablePreview({ table }: TablePreviewProps) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-slate-900/80 p-5 text-slate-100">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{table.file_name}</h3>
          <p className="mt-1 text-sm text-slate-400">{table.columns.length} colunas · {table.row_count} linhas</p>
        </div>
        <span className="rounded-full bg-violet-500/20 px-3 py-1 text-xs uppercase tracking-[0.2em] text-violet-200">Pág {table.page}</span>
      </div>
      <div className="overflow-x-auto rounded-3xl border border-white/10 bg-slate-950/90">
        <table className="min-w-full border-separate border-spacing-0 text-left text-sm text-slate-300">
          <thead className="bg-slate-950/90 text-slate-300">
            <tr>
              {table.columns.map((column) => (
                <th key={column} className="border-b border-white/10 px-4 py-3 font-semibold">{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.preview.map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-slate-900/70">
                {table.columns.map((column) => (
                  <td key={`${rowIndex}-${column}`} className="border-b border-white/10 px-4 py-3 text-slate-300">
                    {String(row[column] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
