import { useState } from 'react';
import { Send, Loader2, BarChart4, AlertCircle } from 'lucide-react';
import { generateDashboard } from '../../services/langchain';
import { useUserStore } from '../../store/userStore';

export function DashboardIAView() {
  const nomeUsuario = useUserStore((state) => state.nomeUsuario);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [charts, setCharts] = useState<Array<{
    id: string;
    title: string;
    explanation: string;
    chart_type: string;
    sql: string;
    image_base64: string;
  }>>([]);

  const handleGenerate = async () => {
    const texto = prompt.trim();
    if (!texto || loading) return;
    setError(null);
    setLoading(true);
    setCharts([]);

    try {
      const response = await generateDashboard(texto, nomeUsuario || undefined);
      setCharts(response.charts || []);
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
    <div className="flex h-full min-h-0 w-full flex-col gap-4 p-6">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <BarChart4 className="h-4 w-4 text-sky-400" />
          <h2 className="text-lg font-semibold text-slate-100">Dashboard com IA</h2>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Descreva o dashboard desejado. Gemini criará consultas SQL, gerará gráficos e explicações.
        </p>
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-white/[0.06] bg-slate-900/30 p-4">
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-slate-300">Prompt do usuário</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={4}
            placeholder="Ex: mostrar receita por mês e comparação de vendas por categoria"
            className="w-full resize-none rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-sm text-slate-100 outline-none transition-colors focus:border-sky-500/70"
            disabled={loading}
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!prompt.trim() || loading}
            className="inline-flex items-center justify-center rounded-2xl bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span className="ml-2">Gerar dashboard</span>
          </button>
          <span className="text-xs text-slate-500">Cada gráfico é criado com um dataframe temporário e expira ao fechar a aba.</span>
        </div>

        {error && (
          <div className="mt-4 rounded-2xl border border-rose-800/50 bg-rose-950/20 px-4 py-3 text-sm text-rose-200">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 text-rose-400" />
              <span>{error}</span>
            </div>
          </div>
        )}

        <div className="mt-6 flex-1 min-h-0 overflow-y-auto pr-1">
          <div className="grid gap-4 sm:grid-cols-2">
            {charts.map((chart) => (
              <div key={chart.id} className="rounded-3xl border border-white/[0.06] bg-slate-950/80 p-4 shadow-lg shadow-black/10">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">{chart.title || 'Gráfico IA'}</h3>
                    <p className="mt-1 text-xs text-slate-500">{chart.chart_type.toUpperCase()} • {chart.id}</p>
                  </div>
                </div>
                {chart.image_base64 ? (
                  <img
                    src={`data:image/png;base64,${chart.image_base64}`}
                    alt={chart.title}
                    className="h-80 w-full rounded-2xl object-contain bg-slate-900"
                  />
                ) : (
                  <div className="flex h-80 items-center justify-center rounded-2xl bg-slate-900/70 text-sm text-slate-500">
                    Imagem não disponível
                  </div>
                )}
                <div className="mt-3 rounded-2xl bg-slate-900/80 p-3 text-sm text-slate-300">
                  <p className="font-semibold text-slate-100">Explicação</p>
                  <p className="mt-1 leading-relaxed">{chart.explanation || 'Sem explicação fornecida.'}</p>
                </div>
                <div className="mt-3 rounded-2xl bg-slate-900/80 p-3 text-xs text-slate-400">
                  <p className="font-semibold text-slate-200">SQL usado</p>
                  <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap text-xs leading-relaxed">{chart.sql}</pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
