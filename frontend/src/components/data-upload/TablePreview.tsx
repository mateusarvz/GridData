import type { TablePreviewResponse } from '../../types/dataUpload';

interface TablePreviewProps {
  table: TablePreviewResponse;
}

export function TablePreview({ table }: TablePreviewProps) {
  const minTableWidth = `${Math.max(100, table.columns.length * 160)}px`;

  return (
    <div className="flex min-h-0 min-w-0 flex-col rounded-[28px] border border-white/10 bg-slate-900/80 p-4 text-slate-100 xl:p-5">
      <div className="mb-4 flex shrink-0 items-center justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-white">{table.file_name}</h3>
          <p className="mt-1 truncate text-sm text-slate-400">
            {table.columns.length} colunas · {table.row_count} linhas
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-violet-500/20 px-3 py-1 text-xs uppercase tracking-[0.2em] text-violet-200">
          Pág {table.page}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto rounded-3xl border border-white/10 bg-slate-950/90">
        <table
          className="table-fixed border-separate border-spacing-0 text-left text-sm text-slate-300"
          style={{ minWidth: minTableWidth, width: '100%' }}
        >
          <thead className="sticky top-0 z-10 bg-slate-950/95 text-slate-300">
            <tr>
              {table.columns.map((column) => (
                <th
                  key={column}
                  className="max-w-[180px] border-b border-white/10 px-4 py-3 text-left font-semibold"
                >
                  <span className="block truncate">{column}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.preview.map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-slate-900/70">
                {table.columns.map((column) => (
                  <td
                    key={`${rowIndex}-${column}`}
                    className="max-w-[240px] border-b border-white/10 px-4 py-3 text-slate-300"
                  >
                    <span className="block truncate">{String(row[column] ?? '')}</span>
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
