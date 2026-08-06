import { useState } from 'react';
import { Send, Loader2, BarChart4, AlertCircle } from 'lucide-react';
import { generateDashboard } from '../../services/langchain';
import { useUserStore } from '../../store/userStore';
import { useDashboardStore } from '../../store/dashboardStore';

interface DashboardIAViewProps {
  onDashboardGenerated?: () => void;
}

export function DashboardIAView({ onDashboardGenerated }: DashboardIAViewProps) {
  const nomeUsuario = useUserStore((state) => state.nomeUsuario);
  const [prompt, setPrompt] = useState('');
  const [isPromptCollapsed, setIsPromptCollapsed] = useState(false);
  const charts = useDashboardStore((state) => state.charts);
  const loading = useDashboardStore((state) => state.loading);
  const error = useDashboardStore((state) => state.error);
  const setCharts = useDashboardStore((state) => state.setCharts);
  const setLoading = useDashboardStore((state) => state.setLoading);
  const setError = useDashboardStore((state) => state.setError);

  const handleGenerate = async () => {
    const texto = prompt.trim();
    if (!texto || loading) return;
    setError(null);
    setLoading(true);
    setCharts([]);
    setIsPromptCollapsed(true);

    try {
      const response = await generateDashboard(texto, nomeUsuario || undefined);
      setCharts(response.charts || []);
      onDashboardGenerated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao gerar dashboard.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col gap-4 pt-2 px-3 pb-3">
      <div className="flex items-center justify-between gap-2 rounded-2xl border border-white/[0.06] bg-slate-900/30 p-3 shadow-sm shadow-black/10">
        <div className="flex items-center gap-2">
          <BarChart4 className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-300">Dashboard com IA</h2>
        </div>
        <button
          type="button"
          onClick={() => setIsPromptCollapsed((prev) => !prev)}
          className="rounded-2xl border border-white/10 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-900"
        >
          {isPromptCollapsed ? 'Mostrar prompt' : 'Minimizar prompt'}
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-3xl border border-white/[0.06] bg-slate-900/60 p-5 shadow-xl shadow-black/20">
        {loading && (
          <div className="mb-4 inline-flex items-center gap-2 rounded-2xl bg-violet-950/60 px-4 py-3 text-sm text-violet-200">
            <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
            <span>Gerando dashboard...</span>
          </div>
        )}
        {!isPromptCollapsed && (
          <div className="mb-4">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={4}
              placeholder="Insira um prompt com instruções para a IA"
              className="w-full resize-none rounded-3xl border border-white/10 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition-colors focus:border-sky-500/70"
              disabled={loading}
            />
          </div>
        )}

        {!isPromptCollapsed && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!prompt.trim() || loading}
              className="inline-flex items-center justify-center rounded-2xl bg-sky-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin text-slate-950" /> : <Send className="h-4 w-4" />}
              <span className="ml-2">{loading ? 'Gerando...' : 'Gerar dashboard'}</span>
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-800/50 bg-rose-950/20 px-4 py-3 text-sm text-rose-200">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 text-rose-400" />
              <span>{error}</span>
            </div>
          </div>
        )}

        <div className="mt-6 flex-1 min-h-0 overflow-y-auto pr-1">
          <div className="grid gap-6 xl:grid-cols-2">
            {charts.map((chart, index) => {
              const isFirstGeneralText = index === 0 && chart.item_type === 'text';

              return (
                <div
                  key={chart.id}
                  className={`rounded-3xl border border-white/[0.08] bg-slate-950/95 p-6 shadow-2xl shadow-black/30 ${
                    chart.item_type === 'text' ? 'xl:col-span-2' : ''
                  }`}
                >
                  <div className="mb-3">
                    <h3 className="text-base font-semibold text-slate-100">{chart.title || 'Dashboard IA'}</h3>
                  </div>

                  {chart.item_type === 'chart' && chart.image_base64 ? (
                    <img
                      key={`${chart.id}-${chart.image_base64.slice(0, 16)}`}
                      src={`data:image/png;base64,${chart.image_base64}`}
                      alt={chart.title}
                      className="h-[28rem] w-full rounded-[1.25rem] object-contain bg-slate-900"
                    />
                  ) : chart.item_type === 'chart' ? (
                    <div className="flex h-[28rem] items-center justify-center rounded-[1.25rem] bg-slate-900/70 text-sm text-slate-500">
                      Imagem não disponível
                    </div>
                  ) : null}

                  {chart.item_type === 'table' && chart.table_data ? (
                    <div className="overflow-x-auto rounded-[1.25rem] bg-slate-900/95 p-4">
                      <div className="mb-3 text-sm text-slate-300">{chart.description}</div>
                      <table className="min-w-full text-left text-sm text-slate-100">
                        <thead>
                          <tr>
                            {chart.table_data.columns.map((col) => (
                              <th key={col} className="border-b border-white/10 px-2 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {chart.table_data.rows.map((row, rowIndex) => (
                            <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-slate-950/40' : ''}>
                              {row.map((value, colIndex) => (
                                <td key={`${rowIndex}-${colIndex}`} className="border-b border-white/05 px-2 py-2 text-xs text-slate-200">
                                  {value === null ? '-' : String(value)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="mt-2 text-xs text-slate-500">{chart.table_data.rows_count} linhas totais</div>
                    </div>
                  ) : null}

                  {chart.item_type === 'card' && (
                    <div className="rounded-[1.25rem] bg-slate-900/95 p-6 text-sm text-slate-200">
                      <p className="font-semibold text-slate-100">Resumo</p>
                      <p className="mt-3 text-base leading-relaxed text-slate-100">{chart.content || chart.description}</p>
                    </div>
                  )}

                  {chart.item_type === 'text' && (
                    <div className="rounded-[1.25rem] bg-slate-900/95 p-6 text-sm text-slate-200">
                      <p className="text-base leading-relaxed whitespace-pre-wrap text-slate-100">{chart.content || chart.description}</p>
                    </div>
                  )}

                  {!isFirstGeneralText && (
                    <div className="mt-3 rounded-2xl bg-slate-900/80 p-3 text-sm text-slate-300">
                      <p className="font-semibold text-slate-100">Descrição</p>
                      <p className="mt-1 leading-relaxed">{chart.description || 'Sem descrição fornecida.'}</p>
                    </div>
                  )}

                  {chart.sql && (
                    <div className="mt-3 rounded-2xl bg-slate-900/80 p-3 text-xs text-slate-400">
                      <p className="font-semibold text-slate-200">SQL usado</p>
                      <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap text-xs leading-relaxed">{chart.sql}</pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
