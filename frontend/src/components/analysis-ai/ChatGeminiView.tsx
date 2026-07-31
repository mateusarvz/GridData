import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, AlertCircle } from 'lucide-react';
import { sendChatMessage } from '../../services/langchain';

interface Mensagem {
  role: 'user' | 'assistant';
  content: string;
}

export function ChatGeminiView() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensagens]);

  const handleSend = async () => {
    const pergunta = input.trim();
    if (!pergunta || loading) return;

    setInput('');
    setError(null);

    const userMsg: Mensagem = { role: 'user', content: pergunta };
    setMensagens((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await sendChatMessage(pergunta);
      const assistantMsg: Mensagem = {
        role: 'assistant',
        content: response.resposta,
      };
      setMensagens((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Erro ao processar pergunta.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {mensagens.length === 0 && !error && (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-center">
              <Bot className="h-10 w-10 text-slate-700" />
              <p className="text-sm text-slate-500">
                Faça perguntas sobre seus dados em linguagem natural.
              </p>
              <p className="text-xs text-slate-600">
                Ex: "Quantas linhas tem na tabela X?" ou "Quais são os registros mais recentes?"
              </p>
            </div>
          </div>
        )}

        {mensagens.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-900/50">
                <Bot className="h-4 w-4 text-violet-300" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-800/80 text-slate-200'
              }`}
            >
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-700">
                <User className="h-4 w-4 text-slate-300" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-900/50">
              <Bot className="h-4 w-4 text-violet-300" />
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-slate-800/80 px-4 py-2.5">
              <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
              <span className="text-sm text-slate-400">Processando...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-rose-800/40 bg-rose-950/20 px-4 py-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
            <p className="text-sm text-rose-300">{error}</p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="mt-3 flex items-end gap-2 border-t border-white/[0.06] pt-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Digite sua pergunta sobre os dados..."
          rows={2}
          disabled={loading}
          className="flex-1 resize-none rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-600 outline-none transition-colors focus:border-violet-500/50 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}