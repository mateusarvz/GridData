import { useState } from 'react';
import { Eye, EyeOff, Database, FileText, Table2, ArrowRight, ChevronDown, ChevronRight, AlertCircle, Loader2, Info, MessageSquare } from 'lucide-react';
import { fetchEstruturaAcessivel, type TabelaSchema, type ColunaSchema } from '../../services/langchain';
import { ChatGeminiView } from './ChatGeminiView';

// ── Sub-components ──

function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'default' | 'info' | 'warning' }) {
  const styles = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    info: 'bg-sky-900/40 text-sky-300 border-sky-700/50',
    warning: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${styles[variant]}`}>
      {children}
    </span>
  );
}

function ColunaRow({ coluna }: { coluna: ColunaSchema }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-slate-900/60 px-3 py-1.5 text-[13px]">
      <span className="font-mono text-slate-100">{coluna.nome}</span>
      <Badge>{coluna.tipo}</Badge>
      {coluna.nullable ? (
        <span className="text-[11px] text-slate-500">nullable</span>
      ) : (
        <span className="text-[11px] text-emerald-400/70">NOT NULL</span>
      )}
    </div>
  );
}

function TabelaCard({ tabela, defaultOpen }: { tabela: TabelaSchema; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-slate-900/40 transition-all">
      {/* Header */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-slate-500" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-500" />
        )}
        <Table2 className="h-4 w-4 shrink-0 text-violet-400" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium text-slate-100">
              {tabela.nome_tabela}
            </span>
            <Badge>{tabela.colunas.length} colunas</Badge>
            <Badge variant="info">{tabela.total_linhas} linhas</Badge>
          </div>
        </div>
        <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-600" />
      </button>

      {/* Expanded content */}
      {open && (
        <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">
          {/* Source info */}
          <div className="mb-3 flex flex-wrap gap-3 text-[12px] text-slate-500">
            {tabela.origem_arquivo && (
              <span className="flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                {tabela.origem_arquivo}
              </span>
            )}
            {tabela.tipo_arquivo && (
              <Badge variant="warning">{tabela.tipo_arquivo}</Badge>
            )}
            {tabela.criado_em && (
              <span>
                Criada em: {new Date(tabela.criado_em).toLocaleDateString('pt-BR')}
              </span>
            )}
          </div>

          {/* Columns */}
          <div className="mb-3 space-y-1">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Colunas
            </div>
            {tabela.colunas.map((col) => (
              <ColunaRow key={col.nome} coluna={col} />
            ))}
          </div>

          {/* Relationship */}
          {tabela.relacionamento && (
            <div className="rounded-md bg-sky-950/20 px-3 py-2">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-sky-400">
                Relacionamento (FK)
              </div>
              <div className="font-mono text-[12px] text-sky-300/80">
                <span className="text-sky-200">{tabela.relacionamento.coluna_local}</span>
                {' → '}
                <span className="text-sky-200">{tabela.relacionamento.referencia}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main View ──

export function AnalysisAIView() {
  const [data, setData] = useState<TabelaSchema[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  const handleFetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchEstruturaAcessivel();
      setData(response.tabelas);
      setVisible(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleHide = () => {
    setVisible(false);
    setData(null);
    setError(null);
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4 p-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Análise com IA</h2>
        <p className="mt-1 text-sm text-slate-500">
          Seus dados serão analisados por inteligência artificial. O agente SQL poderá
          consultar suas tabelas para responder perguntas.
        </p>
      </div>

      {/* Action button */}
      <div className="flex items-center gap-3">
        {!visible ? (
          <button
            type="button"
            onClick={handleFetch}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
            {loading
              ? 'Carregando...'
              : 'Visualizar dados que o LangChain vai ter acesso futuramente'}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleHide}
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-slate-700"
          >
            <EyeOff className="h-4 w-4" />
            Ocultar estrutura
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-800/40 bg-rose-950/20 px-4 py-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
          <div>
            <p className="text-sm font-medium text-rose-300">Erro ao carregar estrutura</p>
            <p className="mt-0.5 text-xs text-rose-400/80">{error}</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {visible && data && data.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/10 py-12">
          <Database className="h-8 w-8 text-slate-600" />
          <p className="text-sm text-slate-500">
            Nenhuma tabela cadastrada para este usuário.
          </p>
          <p className="text-xs text-slate-600">
            Faça upload de arquivos na aba "Carregar Dados" para começar.
          </p>
        </div>
      )}

      {/* Table list */}
      {visible && data && data.length > 0 && (
        <>
          <div className="overflow-y-auto max-h-[40vh] pr-1 space-y-2 rounded-xl scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
            {data.map((tabela) => (
              <TabelaCard
                key={tabela.nome_tabela}
                tabela={tabela}
                defaultOpen={true}
              />
            ))}
          </div>

          {/* Disclaimer */}
          <div className="flex items-start gap-2 rounded-lg bg-slate-900/40 px-3 py-2">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
            <p className="text-[11px] leading-relaxed text-slate-500">
              Os dados reais das linhas não são carregados aqui — apenas a estrutura
              (nomes de tabelas, colunas, tipos e relacionamentos) que o agente de IA
              poderá consultar. As consultas são executadas com permissão somente
              leitura e restritas ao seu usuário.
            </p>
          </div>

          {/* Chat Section */}
          <div className="mt-2">
            <div className="mb-2 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-violet-400" />
              <h3 className="text-sm font-semibold text-slate-200">
                Chat com Gemini
              </h3>
            </div>
            <div className="h-[300px] rounded-xl border border-white/[0.06] bg-slate-900/30 p-3">
              <ChatGeminiView />
            </div>
          </div>
        </>
      )}

      {/* Initial state (no data loaded) */}
      {!visible && !error && (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-2 text-center">
            <Database className="h-10 w-10 text-slate-700" />
            <p className="text-sm text-slate-500">
              Clique no botão acima para visualizar a estrutura que será exposta ao
              LangChain.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
