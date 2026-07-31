import { useState } from 'react';
import type { Relacionamento, TabelaUploadada } from '../../types/schemaAnalysis';
import { TIPO_RELACIONAMENTO_OPTIONS } from '../../types/schemaAnalysis';
import { editarRelacionamento, criarRelacionamento } from '../../services/schemaAnalysis';

interface Props {
  sessionId: string;
  tabelas: TabelaUploadada[];
  relacionamentos: Relacionamento[];
  onRelacionamentosChange: (rels: Relacionamento[]) => void;
}

function ConfiancaBadge({ valor }: { valor: number }) {
  const pct = Math.round(valor * 100);
  const color =
    pct >= 80
      ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20'
      : pct >= 50
        ? 'text-amber-400 bg-amber-400/10 border-amber-400/20'
        : 'text-rose-400 bg-rose-400/10 border-rose-400/20';
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${color}`}>{pct}% conf.</span>;
}

function AcaoBadge({ acao }: { acao?: Relacionamento['acao_gemini'] }) {
  if (!acao) return null;
  const cls =
    acao === 'confirma'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : acao === 'ajusta'
        ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
        : 'border-rose-500/30 bg-rose-500/10 text-rose-300';
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>{acao}</span>;
}

function PapelBadge({ papel }: { papel: 'PK' | 'FK' }) {
  const cls =
    papel === 'PK'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : 'border-violet-500/30 bg-violet-500/10 text-violet-300';
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>{papel}</span>;
}

export function RelationshipEditor({ sessionId, tabelas, relacionamentos, onRelacionamentosChange }: Props) {
  const [adicionando, setAdicionando] = useState(false);
  const [novoRel, setNovoRel] = useState({
    tabela_origem_id: '',
    coluna_origem: '',
    tabela_destino_id: '',
    coluna_destino: '',
    tipo_relacionamento: '1:N' as '1:1' | '1:N' | 'N:N',
  });
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  const tabelaById = Object.fromEntries(tabelas.map((t) => [t.table_id, t]));
  const relacionamentosOrdenados = [...relacionamentos].sort((a, b) => b.grau_confianca - a.grau_confianca);

  const handleToggleAprovado = async (rel: Relacionamento) => {
    if (!rel.id) return;
    const novo = !rel.aprovado;
    try {
      await editarRelacionamento(sessionId, rel.id, { aprovado: novo });
      onRelacionamentosChange(relacionamentos.map((r) => (r.id === rel.id ? { ...r, aprovado: novo } : r)));
    } catch {}
  };

  const handleTipoChange = async (rel: Relacionamento, tipo: string) => {
    if (!rel.id) return;
    try {
      await editarRelacionamento(sessionId, rel.id, { tipo_relacionamento: tipo });
      onRelacionamentosChange(
        relacionamentos.map((r) => (r.id === rel.id ? { ...r, tipo_relacionamento: tipo as '1:1' | '1:N' | 'N:N' } : r))
      );
    } catch {}
  };

  const handleAdicionar = async () => {
    if (!novoRel.tabela_origem_id || !novoRel.coluna_origem || !novoRel.tabela_destino_id || !novoRel.coluna_destino) {
      setErro('Preencha todos os campos.');
      return;
    }
    setSalvando(true);
    setErro('');
    try {
      const criado = await criarRelacionamento(sessionId, novoRel);
      const tOrig = tabelaById[novoRel.tabela_origem_id];
      const tDest = tabelaById[novoRel.tabela_destino_id];
      onRelacionamentosChange([
        ...relacionamentos,
        {
          ...criado,
          nome_tabela_origem: tOrig?.nome_tabela_sugerido ?? '',
          nome_tabela_destino: tDest?.nome_tabela_sugerido ?? '',
        },
      ]);
      setAdicionando(false);
      setNovoRel({
        tabela_origem_id: '',
        coluna_origem: '',
        tabela_destino_id: '',
        coluna_destino: '',
        tipo_relacionamento: '1:N',
      });
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao criar relacionamento.');
    } finally {
      setSalvando(false);
    }
  };

  const colunasFor = (tableId: string) => tabelaById[tableId]?.colunas.map((c) => c.nome) ?? [];

  return (
    <div className="w-full overflow-hidden rounded-[24px] border border-white/10 bg-slate-900/80">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div>
          <h3 className="text-base font-semibold text-white">Relacionamentos</h3>
          <p className="mt-0.5 text-xs text-slate-400">Sugeridos pelo Gemini ou criados manualmente</p>
        </div>
        <button
          type="button"
          onClick={() => setAdicionando(true)}
          className="rounded-xl border border-violet-500/30 bg-violet-500/20 px-3 py-1.5 text-xs font-medium text-violet-300 transition hover:bg-violet-500/30"
        >
          + Adicionar
        </button>
      </div>

      <div className="divide-y divide-white/5">
        {relacionamentos.length === 0 && !adicionando && (
          <p className="px-5 py-8 text-center text-sm text-slate-500">Nenhum relacionamento sugerido. Adicione manualmente se necessário.</p>
        )}

        {relacionamentosOrdenados.map((rel, i) => (
          <div key={rel.id ?? i} className={`flex flex-col gap-2 px-5 py-4 transition-colors ${rel.aprovado ? '' : 'opacity-40'}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex flex-1 flex-wrap items-center gap-2 font-mono text-xs text-slate-200">
                <PapelBadge papel="FK" />
                <span className="text-violet-300">{rel.nome_tabela_origem}</span>
                <span className="text-slate-500">.</span>
                <span>{rel.coluna_origem}</span>
                <span className="mx-1 text-slate-500">&rarr;</span>
                <PapelBadge papel="PK" />
                <span className="text-emerald-300">{rel.nome_tabela_destino}</span>
                <span className="text-slate-500">.</span>
                <span>{rel.coluna_destino}</span>
                {rel.grau_confianca < 0.5 && (
                  <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400">
                    revisar
                  </span>
                )}
                <AcaoBadge acao={rel.acao_gemini} />
              </div>

              <div className="flex flex-shrink-0 items-center gap-2">
                {rel.origem === 'gemini' && <ConfiancaBadge valor={rel.grau_confianca} />}

                <select
                  value={rel.tipo_relacionamento}
                  onChange={(e) => handleTipoChange(rel, e.target.value)}
                  className="rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  {TIPO_RELACIONAMENTO_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={() => handleToggleAprovado(rel)}
                  title={rel.aprovado ? 'Marcar como não aprovado' : 'Marcar como aprovado'}
                  className={`rounded-lg border px-2.5 py-1 text-xs font-medium transition ${
                    rel.aprovado
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20'
                  }`}
                >
                  {rel.aprovado ? 'Aprovado' : 'Não Aprovado'}
                </button>
              </div>
            </div>

            {rel.justificativa && <p className="pl-1 text-xs italic text-slate-500">{rel.justificativa}</p>}
          </div>
        ))}

        {adicionando && (
          <div className="space-y-4 bg-slate-950/40 px-5 py-5">
            <p className="text-sm font-medium text-white">Novo relacionamento</p>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs text-slate-400">Tabela origem</label>
                <select
                  value={novoRel.tabela_origem_id}
                  onChange={(e) => setNovoRel((p) => ({ ...p, tabela_origem_id: e.target.value, coluna_origem: '' }))}
                  className="w-full rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">-- tabela --</option>
                  {tabelas.map((t) => (
                    <option key={t.table_id} value={t.table_id}>
                      {t.nome_tabela_sugerido}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-slate-400">Coluna origem</label>
                <select
                  value={novoRel.coluna_origem}
                  onChange={(e) => setNovoRel((p) => ({ ...p, coluna_origem: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">-- coluna --</option>
                  {colunasFor(novoRel.tabela_origem_id).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-slate-400">Tabela destino</label>
                <select
                  value={novoRel.tabela_destino_id}
                  onChange={(e) => setNovoRel((p) => ({ ...p, tabela_destino_id: e.target.value, coluna_destino: '' }))}
                  className="w-full rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">-- tabela --</option>
                  {tabelas.map((t) => (
                    <option key={t.table_id} value={t.table_id}>
                      {t.nome_tabela_sugerido}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-slate-400">Coluna destino</label>
                <select
                  value={novoRel.coluna_destino}
                  onChange={(e) => setNovoRel((p) => ({ ...p, coluna_destino: e.target.value }))}
                  className="w-full rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">-- coluna --</option>
                  {colunasFor(novoRel.tabela_destino_id).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs text-slate-400">Tipo</label>
                <select
                  value={novoRel.tipo_relacionamento}
                  onChange={(e) =>
                    setNovoRel((p) => ({ ...p, tipo_relacionamento: e.target.value as '1:1' | '1:N' | 'N:N' }))
                  }
                  className="w-full rounded-lg border border-white/10 bg-slate-950/80 px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  {TIPO_RELACIONAMENTO_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {erro && <p className="text-xs text-rose-400">{erro}</p>}

            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleAdicionar}
                disabled={salvando}
                className="rounded-xl bg-violet-500 px-4 py-2 text-xs font-semibold text-white transition hover:bg-violet-400 disabled:opacity-50"
              >
                {salvando ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdicionando(false);
                  setErro('');
                }}
                className="rounded-xl border border-white/10 px-4 py-2 text-xs text-slate-300 transition hover:bg-white/5"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
