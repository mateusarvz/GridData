import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import type { SessaoAnalise, TabelaUploadada, Relacionamento } from '../../types/schemaAnalysis';
import { criarSessaoAnalise, inferirSchema } from '../../services/schemaAnalysis';
import { TableSchemaEditor } from './TableSchemaEditor';
import { RelationshipEditor } from './RelationshipEditor';
import { CommitSqlPreviewModal } from './CommitSqlPreviewModal';

interface Props {
  sessionId?: string | null;
  tabelasIniciais: TabelaUploadada[];
  arquivosCarregados: File[];
  onVoltar: () => void;
  onCommitSuccess: (tabelas: string[]) => void;
  onSchemaReady: (sessionId: string, tabelas: TabelaUploadada[]) => void;
}

export function SchemaReviewView({
  sessionId,
  tabelasIniciais,
  arquivosCarregados,
  onVoltar,
  onCommitSuccess,
  onSchemaReady,
}: Props) {
  const [sessao, setSessao] = useState<SessaoAnalise>({
    session_id: sessionId ?? '',
    status: tabelasIniciais.length > 0 ? 'aguardando_analise' : 'sem_dados',
    total_arquivos: tabelasIniciais.length,
    tabelas: tabelasIniciais,
    relacionamentos: [],
  });
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState('');
  const [geminiUsado, setGeminiUsado] = useState(false);
  const [showCommit, setShowCommit] = useState(false);

  const temDados = arquivosCarregados.length > 0 || sessao.tabelas.length > 0;
  const analisado = sessao.status !== 'aguardando_analise' && sessao.status !== 'sem_dados';
  const sessionAtiva = sessionId ?? sessao.session_id;
  const isMultiArquivo = sessao.total_arquivos > 1;

  const handleAnalisarSchema = async () => {
    if (arquivosCarregados.length === 0) return;
    setProcessando(true);
    setErro('');
    try {
      const { session_id, tabelas } = await criarSessaoAnalise(arquivosCarregados);
      const resultado = await inferirSchema(session_id);
      setSessao(resultado);
      setGeminiUsado(true);
      onSchemaReady(session_id, tabelas);
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Falha ao analisar schema.');
    } finally {
      setProcessando(false);
    }
  };

  const handleColunaEditada = (tableId: string, colName: string, novoTipo: string) => {
    setSessao((prev) => ({
      ...prev,
      tabelas: prev.tabelas.map((t) =>
        t.table_id !== tableId
          ? t
          : {
              ...t,
              colunas: t.colunas.map((c) =>
                c.nome !== colName ? c : { ...c, tipo_sugerido: novoTipo, editado_pelo_usuario: true }
              ),
            }
      ),
    }));
  };

  const handleRelacionamentosChange = (rels: Relacionamento[]) => {
    setSessao((prev) => ({ ...prev, relacionamentos: rels }));
  };

  if (!temDados) {
    return (
      <div className="w-full min-w-0 rounded-[32px] border border-white/10 bg-slate-950/80 p-8 shadow-xl shadow-slate-950/20">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Revisar Schema</p>
            <h2 className="mt-3 text-2xl font-semibold text-white">Não há dados para revisar</h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Carregue arquivos na aba de upload para habilitar a análise de schema.
            </p>
          </div>

          <button
            type="button"
            onClick={handleAnalisarSchema}
            disabled={processando || arquivosCarregados.length === 0}
            className="group flex h-24 w-24 items-center justify-center rounded-full border border-white/10 bg-gradient-to-br from-slate-700 via-slate-600 to-violet-900 text-slate-200 shadow-lg shadow-black/30 transition hover:scale-105 hover:border-violet-400/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Reanalisar schema"
            title="Reanalisar schema"
          >
            <RefreshCw className={`h-10 w-10 transition ${processando ? 'animate-spin' : 'opacity-90 group-hover:opacity-100'}`} />
          </button>
        </div>
      </div>
    );
  }

  if (!analisado) {
    return (
      <div className="w-full min-w-0 space-y-6">
        <div className="w-full min-w-0 rounded-[32px] border border-white/10 bg-slate-950/80 p-8 shadow-xl shadow-slate-950/20">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Revisar Schema</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">Arquivos prontos para análise</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                Clique em Analisar schema para inferir tipos, relacionamentos e preparar a revisão.
              </p>
            </div>
            <button
              type="button"
              onClick={handleAnalisarSchema}
              disabled={processando}
              className="rounded-2xl bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {processando ? 'Analisando...' : 'Analisar schema'}
            </button>
          </div>

          {erro && <div className="mt-5 rounded-2xl bg-rose-500/10 p-4 text-sm text-rose-200">{erro}</div>}
        </div>

        <div className="w-full min-w-0 rounded-[28px] border border-white/10 bg-slate-950/80 p-6">
          <h3 className="text-sm font-medium uppercase tracking-wider text-slate-400">Arquivos carregados</h3>
          <div className="mt-4 grid gap-3">
            {arquivosCarregados.map((file) => (
              <div key={file.name} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white">
                {file.name}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-w-0 space-y-6">
      <div className="flex w-full flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={onVoltar}
            className="mb-2 flex items-center gap-1.5 text-sm text-slate-400 transition hover:text-white"
          >
            ← Voltar ao upload
          </button>
          <h2 className="text-xl font-semibold text-white">Revisão de Schema</h2>
          <p className="mt-1 text-sm text-slate-400">
            {sessao.total_arquivos} arquivo(s) carregado(s) · Revise os tipos antes de inserir no Supabase
          </p>
        </div>
        <div className="flex shrink-0 gap-3 mr-2">
          <button
            type="button"
            onClick={() => setShowCommit(true)}
            className="rounded-2xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-400"
          >
            Inserir no Supabase →
          </button>
        </div>
      </div>

      {!isMultiArquivo && (
        <div className="w-full rounded-2xl border border-white/10 bg-slate-800/60 p-4 text-sm text-slate-300">
          Apenas um arquivo selecionado - nenhuma chave primária ou estrangeira será criada automaticamente.
          Você pode revisar os tipos de coluna sugeridos abaixo.
        </div>
      )}

      {geminiUsado && !erro && (
        <div className="w-full rounded-2xl border border-violet-500/20 bg-violet-500/10 px-4 py-3 text-sm text-violet-300">
          Tipos e relacionamentos sugeridos pelo Gemini. Revise e edite antes de confirmar.
        </div>
      )}
      {erro && <div className="w-full rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-300">{erro}</div>}

      <div className="space-y-4 w-full">
        <h3 className="px-1 text-sm font-medium uppercase tracking-wider text-slate-400">
          Tabelas ({sessao.tabelas.length})
        </h3>
        {sessao.tabelas.map((tabela) => (
          <TableSchemaEditor
            key={tabela.table_id}
            tabela={tabela}
            sessionId={sessionAtiva}
            onColunaEditada={handleColunaEditada}
          />
        ))}
      </div>

      {isMultiArquivo && (
        <div className="space-y-3 w-full">
          <h3 className="px-1 text-sm font-medium uppercase tracking-wider text-slate-400">Relacionamentos</h3>
          <RelationshipEditor
            sessionId={sessionAtiva}
            tabelas={sessao.tabelas}
            relacionamentos={sessao.relacionamentos}
            onRelacionamentosChange={handleRelacionamentosChange}
          />
        </div>
      )}

      {showCommit && (
        <CommitSqlPreviewModal
          sessionId={sessionAtiva}
          onClose={() => setShowCommit(false)}
          onSuccess={(tabelas) => {
            setShowCommit(false);
            onCommitSuccess(tabelas);
          }}
        />
      )}
    </div>
  );
}
