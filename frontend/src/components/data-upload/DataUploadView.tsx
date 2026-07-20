import { useState } from 'react';
import { DataUploadModal } from './DataUploadModal';
import { LoadedTablesPanel } from './LoadedTablesPanel';
import { TablePreview } from './TablePreview';
import { clearSessionTables, listSessionTables, uploadDataFiles } from '../../services/dataUpload';
import { useDataSessionStore } from '../../store/dataSessionStore';
import type { TablePreviewResponse } from '../../types/dataUpload';

interface Props {
  onFilesLoaded: (files: File[]) => void;
  onSessionCleared: () => void;
}

export function DataUploadView({ onFilesLoaded, onSessionCleared }: Props) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [preview, setPreview] = useState<TablePreviewResponse | null>(null);
  const [previewTableId, setPreviewTableId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const tables = useDataSessionStore((state) => state.tables);
  const setTables = useDataSessionStore((state) => state.setTables);

  const loadTables = async () => {
    if (!sessionReady) return;
    setIsLoading(true);
    try {
      const sessionTables = await listSessionTables();
      setTables(sessionTables);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar tabelas.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (files: File[]) => {
    setError('');
    const result = await uploadDataFiles(files);
    setTables(result);
    const firstTableId = result[0]?.table_id ?? null;
    setPreviewTableId(firstTableId);
    setPreview(
      result[0]
        ? {
            table_id: result[0].table_id,
            file_name: result[0].file_name,
            columns: result[0].columns,
            row_count: result[0].row_count,
            preview: result[0].preview,
            page: 1,
            page_size: result[0].preview.length || 20,
          }
        : null
    );
    setSessionReady(true);
    setIsModalOpen(false);
    onFilesLoaded(files);
  };

  const handleSelectTable = (tableId: string) => {
    if (tableId === previewTableId) return;
    const selected = tables.find((table) => table.table_id === tableId);
    if (!selected) return;
    setPreviewTableId(tableId);
    setPreview({
      table_id: selected.table_id,
      file_name: selected.file_name,
      columns: selected.columns,
      row_count: selected.row_count,
      preview: selected.preview,
      page: 1,
      page_size: selected.preview.length || 20,
    });
  };

  const handleClearSession = async () => {
    setIsClearing(true);
    try {
      await clearSessionTables();
      setTables([]);
      setPreview(null);
      setPreviewTableId(null);
      setSessionReady(false);
      onSessionCleared();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao limpar sessao.');
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4 overflow-hidden">
      <div className="flex w-full shrink-0 flex-col gap-3 rounded-[28px] border border-white/10 bg-slate-950/80 px-4 py-3 shadow-xl shadow-slate-950/20 xl:px-5 xl:py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-white xl:text-xl">Carregar Dados</h2>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-400 xl:text-sm xl:leading-6">
              Envie arquivos CSV, Parquet ou XLSX para processar em memoria.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                if (sessionReady) {
                  loadTables();
                }
                setIsModalOpen(true);
              }}
              className="rounded-2xl bg-violet-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-400"
            >
              Carregar Dados
            </button>
            <button
              type="button"
              onClick={handleClearSession}
              disabled={isClearing}
              className="rounded-2xl border border-white/10 bg-transparent px-4 py-2.5 text-sm text-slate-200 transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isClearing ? 'Limpando...' : 'Limpar sessao'}
            </button>
          </div>
        </div>

        {isLoading && <div className="text-sm text-slate-300">Carregando...</div>}
        {error && <div className="rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}
      </div>

      <div className="grid min-h-0 flex-1 w-full gap-4 overflow-hidden xl:grid-cols-[minmax(0,340px)_minmax(0,1fr)] xl:gap-6">
        <LoadedTablesPanel tables={tables} onSelectTable={handleSelectTable} />
        {preview ? (
          <TablePreview table={preview} />
        ) : (
          <div className="flex min-h-0 w-full items-center justify-center rounded-[28px] border border-white/10 bg-slate-950/80 p-6 text-center text-slate-400">
            Selecione uma tabela ou carregue arquivos para visualizar os dados.
          </div>
        )}
      </div>

      {isModalOpen && <DataUploadModal onClose={() => setIsModalOpen(false)} onUpload={handleUpload} />}
    </div>
  );
}
