import { useState } from 'react';
import { commitSessao } from '../../services/schemaAnalysis';

interface Props {
  sessionId: string;
  onClose: () => void;
  onSuccess: (tabelas: string[]) => void;
}

export function CommitSqlPreviewModal({ sessionId, onClose, onSuccess }: Props) {
  const [step, setStep] = useState<'preview' | 'confirmando' | 'sucesso' | 'erro'>('preview');
  const [sql, setSql] = useState('');
  const [tabelasCriadas, setTabelasCriadas] = useState<string[]>([]);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  // Gerar SQL para preview primeiro
  const handleGerarPreview = async () => {
    setCarregando(true);
    try {
      const result = await commitSessao(sessionId);
      setSql(result.sql_gerado);
      setTabelasCriadas(result.tabelas_criadas);
      setStep('sucesso');
      onSuccess(result.tabelas_criadas);
    } catch (err) {
      setErro(err instanceof Error ? err.message : 'Erro ao inserir no Supabase.');
      setStep('erro');
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />

      <div className="relative z-10 w-full max-w-2xl rounded-[28px] border border-white/10 bg-slate-900 shadow-2xl shadow-slate-950/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
          <h2 className="text-base font-semibold text-white">
            {step === 'sucesso' ? '✅ Schema inserido com sucesso' :
             step === 'erro' ? '❌ Erro ao inserir schema' :
             'Confirmar inserção no Supabase'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition text-lg flex items-center justify-center"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Estado inicial */}
          {step === 'preview' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-300">
                Esta ação irá gerar o DDL a partir do schema revisado e executá-lo no Supabase.
                As tabelas de staging serão removidas após o commit.
              </p>
              <div className="rounded-xl bg-amber-400/10 border border-amber-400/20 p-4 text-sm text-amber-300">
                ⚠️ Esta operação não pode ser desfeita. Verifique os tipos e relacionamentos antes de continuar.
              </div>
            </div>
          )}

          {/* Sucesso — SQL gerado */}
          {step === 'sucesso' && (
            <div className="space-y-4">
              <div className="rounded-xl bg-emerald-400/10 border border-emerald-400/20 p-3 text-sm text-emerald-300">
                🎉 {tabelasCriadas.length} tabela(s) criada(s): {tabelasCriadas.join(', ')}
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-2 uppercase tracking-wider">SQL Executado</p>
                <pre className="text-xs text-slate-300 bg-slate-950/80 rounded-xl border border-white/10 p-4 overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed">
                  {sql}
                </pre>
              </div>
            </div>
          )}

          {/* Erro */}
          {step === 'erro' && (
            <div className="space-y-3">
              <div className="rounded-xl bg-rose-500/10 border border-rose-500/20 p-4 text-sm text-rose-300">
                {erro}
              </div>
              {sql && (
                <div>
                  <p className="text-xs text-slate-400 mb-2">SQL gerado (não executado):</p>
                  <pre className="text-xs text-slate-300 bg-slate-950/80 rounded-xl border border-white/10 p-4 overflow-x-auto whitespace-pre-wrap font-mono">
                    {sql}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-300 hover:bg-white/5 transition"
          >
            {step === 'sucesso' || step === 'erro' ? 'Fechar' : 'Cancelar'}
          </button>

          {step === 'preview' && (
            <button
              type="button"
              onClick={handleGerarPreview}
              disabled={carregando}
              className="rounded-xl bg-violet-500 px-5 py-2 text-sm font-semibold text-white hover:bg-violet-400 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {carregando && (
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              {carregando ? 'Inserindo...' : 'Inserir no Supabase'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
