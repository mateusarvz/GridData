import { useState } from 'react';
import type { SessaoAnalise, TabelaUploadada, Relacionamento } from '../../types/schemaAnalysis';
import { inferirSchema } from '../../services/schemaAnalysis';
import { TableSchemaEditor } from './TableSchemaEditor';
import { RelationshipEditor } from './RelationshipEditor';
import { CommitSqlPreviewModal } from './CommitSqlPreviewModal';

interface Props {
  sessionId: string;
  tabelasIniciais: TabelaUploadada[];
  onVoltar: () => void;
  onCommitSuccess: (tabelas: string[]) => void;
}

export function SchemaReviewView({ sessionId, tabelasIniciais, onVoltar, onCommitSuccess }: Props) {
  const [sessao, setSessao] = useState<SessaoAnalise>({
    session_id: sessionId,
    status: 'aguardando_analise',
    total_arquivos: tabelasIniciais.length,
    tabelas: tabelasIniciais,
    relacionamentos: [],
  });
  const [inferindo, setInferindo] = useState(false);
  const [erroInferencia, setErroInferencia] = useState('');
  const [geminiUsado, setGeminiUsado] = useState(false);
  const [showCommit, setShowCommit] = useState(false);

  const isMultiArquivo = sessao.total_arquivos > 1;
  const analisado = sessao.status !== 'aguardando_analise';

  const handleInferir = async () => {
    setInferindo(true);
    setErroInferencia('');
    try {
      const resultado = await inferirSchema(sessionId);
      setSessao(resultado);
      setGeminiUsado(true);
    } catch (err) {
      setErroInferencia(
        err instanceof Error
          ? err.message
          : 'Falha ao chamar o Gemini. Você pode editar os tipos manualmente abaixo.'
      );
    } finally {
      setInferindo(false);
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={onVoltar}
            className="mb-2 flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition"
          >
            ← Voltar ao upload
          </button>
          <h2 className="text-xl font-semibold text-white">Revisão de Schema</h2>
          <p className="text-sm text-slate-400 mt-1">
            {sessao.total_arquivos} arquivo(s) carregado(s) · Revise os tipos antes de inserir no Supabase
          </p>
        </div>
        <div className="flex gap-3">
          {!analisado && (
            <button
              type="button"
              onClick={handleInferir}
              disabled={inferindo}
              className="flex items-center gap-2 rounded-2xl bg-violet-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-violet-400 transition disabled:opacity-50"
            >
              {inferindo ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Analisando com Gemini…
                </>
              ) : (
                '✨ Analisar com Gemini'
              )}
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowCommit(true)}
            className="rounded-2xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-400 transition"
          >
            Inserir no Supabase →
          </button>
        </div>
      </div>

      {/* Aviso arquivo único */}
      {!isMultiArquivo && (
        <div className="rounded-2xl bg-slate-800/60 border border-white/10 p-4 text-sm text-slate-300">
          ℹ️ Apenas um arquivo selecionado — nenhuma chave primária ou estrangeira será criada
          automaticamente. Você pode revisar os tipos de coluna sugeridos abaixo.
        </div>
      )}

      {/* Status Gemini */}
      {geminiUsado && !erroInferencia && (
        <div className="rounded-2xl bg-violet-500/10 border border-violet-500/20 px-4 py-3 text-sm text-violet-300">
          ✨ Tipos e relacionamentos sugeridos pelo Gemini. Revise e edite antes de confirmar.
        </div>
      )}
      {erroInferencia && (
        <div className="rounded-2xl bg-amber-400/10 border border-amber-400/20 px-4 py-3 text-sm text-amber-300">
          ⚠️ {erroInferencia}
        </div>
      )}

      {/* Tabelas */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider px-1">
          Tabelas ({sessao.tabelas.length})
        </h3>
        {sessao.tabelas.map((tabela) => (
          <TableSchemaEditor
            key={tabela.table_id}
            tabela={tabela}
            sessionId={sessionId}
            onColunaEditada={handleColunaEditada}
          />
        ))}
      </div>

      {/* Relacionamentos — só para múltiplos arquivos */}
      {isMultiArquivo && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider px-1">
            Relacionamentos
          </h3>
          <RelationshipEditor
            sessionId={sessionId}
            tabelas={sessao.tabelas}
            relacionamentos={sessao.relacionamentos}
            onRelacionamentosChange={handleRelacionamentosChange}
          />
        </div>
      )}

      {/* Modal de commit */}
      {showCommit && (
        <CommitSqlPreviewModal
          sessionId={sessionId}
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
