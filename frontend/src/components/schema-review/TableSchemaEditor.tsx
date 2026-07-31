import { useState } from 'react';
import type { TabelaUploadada } from '../../types/schemaAnalysis';
import { POSTGRES_TYPES } from '../../types/schemaAnalysis';
import { editarColuna, editarNuloColuna } from '../../services/schemaAnalysis';

interface Props {
  tabela: TabelaUploadada;
  sessionId: string;
  onColunaEditada: (table_id: string, column_name: string, novo_tipo: string) => void;
}

export function TableSchemaEditor({ tabela, sessionId, onColunaEditada }: Props) {
  const [editando, setEditando] = useState<Record<string, boolean>>({});
  const [erros, setErros] = useState<Record<string, string>>({});

  const handleTipoChange = async (colName: string, novoTipo: string) => {
    setEditando((prev) => ({ ...prev, [colName]: true }));
    setErros((prev) => ({ ...prev, [colName]: '' }));
    try {
      await editarColuna(sessionId, tabela.table_id, colName, novoTipo);
      onColunaEditada(tabela.table_id, colName, novoTipo);
    } catch (err) {
      setErros((prev) => ({
        ...prev,
        [colName]: err instanceof Error ? err.message : 'Erro ao salvar.',
      }));
    } finally {
      setEditando((prev) => ({ ...prev, [colName]: false }));
    }
  };

  const handleNuloChange = async (colName: string, nuloPermitido: boolean) => {
    setEditando((prev) => ({ ...prev, [`${colName}__nulo`]: true }));
    setErros((prev) => ({ ...prev, [`${colName}__nulo`]: '' }));
    try {
      await editarNuloColuna(sessionId, tabela.table_id, colName, nuloPermitido);
      onColunaEditada(tabela.table_id, colName, tabela.colunas.find((c) => c.nome === colName)?.tipo_sugerido || '');
    } catch (err) {
      setErros((prev) => ({
        ...prev,
        [`${colName}__nulo`]: err instanceof Error ? err.message : 'Erro ao salvar.',
      }));
    } finally {
      setEditando((prev) => ({ ...prev, [`${colName}__nulo`]: false }));
    }
  };

  return (
    <div className="w-full overflow-hidden rounded-[24px] border border-white/10 bg-slate-900/80">
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
        <div className="min-w-0">
          <p className="mb-0.5 text-xs text-slate-400">{tabela.nome_arquivo}</p>
          <h3 className="truncate font-mono text-base font-semibold text-white">{tabela.nome_tabela_sugerido}</h3>
        </div>
        <span className="shrink-0 rounded-full border border-violet-500/20 bg-violet-500/15 px-3 py-1 text-xs text-violet-300">
          {tabela.total_linhas.toLocaleString('pt-BR')} linhas
        </span>
      </div>

      <div className="w-full overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-500">
              <th className="px-5 py-3 text-left font-medium">Coluna</th>
              <th className="px-5 py-3 text-left font-medium">Tipo bruto</th>
              <th className="px-5 py-3 text-left font-medium">Tipo Postgres</th>
              <th className="px-5 py-3 text-left font-medium">Permite nulo</th>
              <th className="px-5 py-3 text-center font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {tabela.colunas.map((col) => (
              <tr
                key={col.nome}
                className={`transition-colors ${col.editado_pelo_usuario ? 'bg-violet-500/5' : 'hover:bg-white/[0.02]'}`}
              >
                <td className="px-5 py-3">
                  <span className="rounded-md bg-white/5 px-2 py-0.5 font-mono text-xs text-white">
                    {col.nome}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <span className="font-mono text-xs text-slate-500">{col.tipo_bruto}</span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-col gap-1">
                    <select
                      value={col.tipo_sugerido || ''}
                      onChange={(e) => handleTipoChange(col.nome, e.target.value)}
                      disabled={editando[col.nome]}
                      className={`rounded-lg border bg-slate-950/80 px-2 py-1.5 text-xs text-white transition focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:cursor-not-allowed disabled:opacity-50 ${
                        col.editado_pelo_usuario ? 'border-violet-500/40' : 'border-white/10 hover:border-white/20'
                      }`}
                    >
                      <option value="">-- selecione --</option>
                      {POSTGRES_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    {erros[col.nome] && <p className="text-xs text-rose-400">{erros[col.nome]}</p>}
                  </div>
                </td>
                <td className="px-5 py-3">
                  <div className="flex flex-col gap-1">
                    <select
                      value={col.nulo_permitido ? 'sim' : 'nao'}
                      onChange={(e) => handleNuloChange(col.nome, e.target.value === 'sim')}
                      disabled={editando[`${col.nome}__nulo`]}
                      className={`rounded-lg border bg-slate-950/80 px-2 py-1.5 text-xs text-white transition focus:outline-none focus:ring-1 focus:ring-violet-500 disabled:cursor-not-allowed disabled:opacity-50 ${
                        col.editado_pelo_usuario ? 'border-violet-500/40' : 'border-white/10 hover:border-white/20'
                      }`}
                    >
                      <option value="sim">Sim</option>
                      <option value="nao">Não</option>
                    </select>
                    {erros[`${col.nome}__nulo`] && <p className="text-xs text-rose-400">{erros[`${col.nome}__nulo`]}</p>}
                  </div>
                </td>
                <td className="px-5 py-3 text-center">
                  {editando[col.nome] || editando[`${col.nome}__nulo`] ? (
                    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                      <span className="h-3 w-3 animate-spin rounded-full border border-slate-400 border-t-transparent" />
                      Salvando
                    </span>
                  ) : col.editado_pelo_usuario ? (
                    <span className="inline-flex items-center gap-1 text-xs text-violet-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />
                      Editado
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      Gemini
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
