import { useEffect, useState } from 'react';
import { DataUploadModal } from './DataUploadModal';
import { LoadedTablesPanel } from './LoadedTablesPanel';
import { TablePreview } from './TablePreview';
import { listSessionTables, uploadDataFiles, getTablePreview, clearSessionTables } from '../../services/dataUpload';
import { criarSessaoAnalise } from '../../services/schemaAnalysis';
import { useDataSessionStore } from '../../store/dataSessionStore';
import type { TablePreviewResponse } from '../../types/dataUpload';
import type { TabelaUploadada } from '../../types/schemaAnalysis';

interface Props {
  onIrParaRevisao: (sessionId: string, tabelas: TabelaUploadada[]) => void;
}

export function DataUploadView({ onIrParaRevisao }: Props) {
  const [activeTableId, setActiveTableId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [preview, setPreview] = useState<TablePreviewResponse | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [criandoSessao, setCriandoSessao] = useState(false);
  const [ultimosArquivos, setUltimosArquivos] = useState<FileList | null>(null);
  const tables = useDataSessionStore((state) => state.tables);
  const setTables = useDataSessionStore((state) => state.setTables);

  const loadTables = async () => {
    setIsLoading(true);
    try {
      const result = await listSessionTables();
      setTables(result);
      if (result.length === 0) {
        setActiveTableId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar tabelas.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (files: FileList) => {
    setError('');
    const result = await uploadDataFiles(files);
    setTables(result);
    setActiveTableId(result[0]?.table_id ?? null);
    setIsModalOpen(false);
    setUltimosArquivos(files);
    await fetchPreview(result[0]?.table_id ?? null);
  };

  const fetchPreview = async (tableId: string | null) => {
    if (!tableId) {
      setPreview(null);
      return;
    }
    setIsLoading(true);
    try {
      const data = await getTablePreview(tableId);
      setPreview(data);
      setActiveTableId(tableId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar preview.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearSession = async () => {
    setIsClearing(true);
    try {
      await clearSessionTables();
      setTables([]);
      setActiveTableId(null);
      setPreview(null);
      setUltimosArquivos(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao limpar sessão.');
    } finally {
      setIsClearing(false);
    }
  };

  const handleAnalisarSchema = async () => {
    if (!ultimosArquivos) return;
    setCriandoSessao(true);
    setError('');
    try {
      const { session_id, tabelas } = await criarSessaoAnalise(ultimosArquivos);
      onIrParaRevisao(session_id, tabelas);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao iniciar análise de schema.');
    } finally {
      setCriandoSessao(false);
    }
  };

  useEffect(() => {
    loadTables();
  }, []);

  useEffect(() => {
    if (!activeTableId) return;
    fetchPreview(activeTableId);
  }, [activeTableId]);

  return (
    <div className="space-y-8 h-[calc(100vh-13rem)] overflow-y-auto pr-2">
      <div className="flex flex-col gap-4 rounded-[32px] border border-white/10 bg-slate-950/80 p-6 shadow-xl shadow-slate-950/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-white">Upload de dados em memória</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Arquivos enviados são convertidos para DataFrame no backend e mantidos apenas em memória/redis com TTL.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="rounded-2xl bg-violet-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-violet-400"
            >
              Carregar Dados
            </button>
            {ultimosArquivos && (
              <button
                type="button"
                onClick={handleAnalisarSchema}
                disabled={criandoSessao}
                className="rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {criandoSessao && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {criandoSessao ? 'Preparando...' : '✨ Analisar Schema'}
              </button>
            )}
            <button
              type="button"
              onClick={handleClearSession}
              disabled={isClearing}
              className="rounded-2xl border border-white/10 bg-transparent px-4 py-3 text-sm text-slate-200 transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isClearing ? 'Limpando...' : 'Limpar sessão'}
            </button>
          </div>
        </div>

        {isLoading && <div className="text-sm text-slate-300">Carregando...</div>}
        {error && <div className="rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>}
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <LoadedTablesPanel tables={tables} onSelectTable={setActiveTableId} />
        {preview ? (
          <TablePreview table={preview} />
        ) : (
          <div className="rounded-[28px] border border-white/10 bg-slate-950/80 p-6 text-slate-400">
            Selecione uma tabela ou carregue arquivos para visualizar os dados.
          </div>
        )}
      </div>

      {isModalOpen && <DataUploadModal onClose={() => setIsModalOpen(false)} onUpload={handleUpload} />}
    </div>
  );
}
