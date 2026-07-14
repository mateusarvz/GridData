import { useState } from 'react';
import type { TabelaUploadada } from '../../types/schemaAnalysis';
import { POSTGRES_TYPES } from '../../types/schemaAnalysis';
import { editarColuna } from '../../services/schemaAnalysis';

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

  return (
    <div className="rounded-[24px] border border-white/10 bg-slate-900/80 overflow-hidden">
      {/* Header da tabela */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
        <div>
          <p className="text-xs text-slate-400 mb-0.5">{tabela.nome_arquivo}</p>
          <h3 className="text-base font-semibold text-white font-mono">
            {tabela.nome_tabela_sugerido}
          </h3>
        </div>
        <span className="rounded-full bg-violet-500/15 px-3 py-1 text-xs text-violet-300 border border-violet-500/20">
          {tabela.total_linhas.toLocaleString('pt-BR')} linhas
        </span>
      </div>

      {/* Grid de colunas */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 uppercase tracking-wider border-b border-white/5">
              <th className="text-left px-5 py-3 font-medium">Coluna</th>
              <th className="text-left px-5 py-3 font-medium">Tipo bruto</th>
              <th className="text-left px-5 py-3 font-medium">Tipo Postgres</th>
              <th className="text-left px-5 py-3 font-medium">Permite nulo</th>
              <th className="px-5 py-3 font-medium text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {tabela.colunas.map((col) => (
              <tr
                key={col.nome}
                className={`transition-colors ${
                  col.editado_pelo_usuario ? 'bg-violet-500/5' : 'hover:bg-white/[0.02]'
                }`}
              >
                {/* Nome da coluna */}
                <td className="px-5 py-3">
                  <span className="font-mono text-white text-xs bg-white/5 px-2 py-0.5 rounded-md">
                    {col.nome}
                  </span>
                </td>

                {/* Tipo bruto */}
                <td className="px-5 py-3">
                  <span className="text-slate-500 font-mono text-xs">{col.tipo_bruto}</span>
                </td>

                {/* Seletor de tipo */}
                <td className="px-5 py-3">
                  <div className="flex flex-col gap-1">
                    <select
                      value={col.tipo_sugerido || ''}
                      onChange={(e) => handleTipoChange(col.nome, e.target.value)}
                      disabled={editando[col.nome]}
                      className={`rounded-lg border text-xs px-2 py-1.5 bg-slate-950/80 text-white transition
                        focus:outline-none focus:ring-1 focus:ring-violet-500
                        disabled:opacity-50 disabled:cursor-not-allowed
                        ${
                          col.editado_pelo_usuario
                            ? 'border-violet-500/40'
                            : 'border-white/10 hover:border-white/20'
                        }`}
                    >
                      <option value="">-- selecione --</option>
                      {POSTGRES_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    {erros[col.nome] && (
                      <p className="text-xs text-rose-400">{erros[col.nome]}</p>
                    )}
                  </div>
                </td>

                {/* Permite nulo */}
                <td className="px-5 py-3">
                  <span className={`text-xs ${col.nulo_permitido ? 'text-slate-400' : 'text-amber-400'}`}>
                    {col.nulo_permitido ? 'Sim' : 'Não'}
                  </span>
                </td>

                {/* Badge de status */}
                <td className="px-5 py-3 text-center">
                  {editando[col.nome] ? (
                    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                      <span className="w-3 h-3 border border-slate-400 border-t-transparent rounded-full animate-spin" />
                      Salvando
                    </span>
                  ) : col.editado_pelo_usuario ? (
                    <span className="inline-flex items-center gap-1 text-xs text-violet-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                      Editado
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
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
