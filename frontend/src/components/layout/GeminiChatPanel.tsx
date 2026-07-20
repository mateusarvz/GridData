import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Bot, Loader2, Send } from 'lucide-react';
import { getGeminiStatus, sendGeminiChat } from '../../services/gemini';

type ChatMessage = {
  role: 'user' | 'assistant';
  text: string;
};

export function GeminiChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: 'Teste aqui. Manda uma pergunta curta.' },
  ]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'checking' | 'connected' | 'offline'>('checking');
  const [statusError, setStatusError] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const result = await getGeminiStatus();
        setStatus(result.connected ? 'connected' : 'offline');
        setStatusError(result.error || '');
      } catch (error) {
        setStatus('offline');
        setStatusError(error instanceof Error ? error.message : 'Erro ao testar Gemini.');
      }
    })();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || loading) return;

    setMessages((current) => [...current, { role: 'user', text }]);
    setPrompt('');
    setLoading(true);

    try {
      const result = await sendGeminiChat(text);
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: result.error ? `Erro: ${result.error}` : result.response || 'Sem resposta.' },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: error instanceof Error ? `Erro: ${error.message}` : 'Erro ao falar com Gemini.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-slate-900 text-cyan-300">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-100">Chat com IA</div>
          <div className="text-[11px] text-slate-500">Teste simples de conexão e resposta.</div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Status</div>
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span
            className={`h-2.5 w-2.5 rounded-full ${
              status === 'connected' ? 'bg-emerald-400' : status === 'offline' ? 'bg-rose-400' : 'bg-amber-300'
            }`}
          />
          <span className="text-slate-100">
            {status === 'connected' ? 'Gemini conectado' : status === 'offline' ? 'Gemini offline' : 'Testando conexão'}
          </span>
        </div>
        {statusError && <div className="mt-2 text-xs text-slate-400">{statusError}</div>}
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-3xl border border-white/10 bg-slate-950/60 p-3">
        <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Teste</div>
        <div className="sidebar-scroll flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                message.role === 'user'
                  ? 'ml-auto bg-cyan-500/15 text-cyan-50'
                  : 'mr-auto bg-white/5 text-slate-100'
              }`}
            >
              {message.text}
            </div>
          ))}
          {loading && (
            <div className="mr-auto flex items-center gap-2 rounded-2xl bg-white/5 px-3 py-2 text-sm text-slate-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Gemini pensando
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
          <input
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Digite e teste..."
            className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none transition-colors placeholder:text-slate-500 focus:border-cyan-400/60"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="inline-flex items-center gap-2 rounded-2xl bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
