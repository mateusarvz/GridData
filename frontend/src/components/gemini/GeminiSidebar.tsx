import { useEffect, useRef, useState } from 'react';
import { ChevronRight, Sparkles, SendHorizontal } from 'lucide-react';
import { api } from '../../services/api';

interface Message {
  role: 'user' | 'gemini';
  text: string;
}

export function GeminiSidebar() {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'gemini', text: 'Olá. Como posso te ajudar hoje?' },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt) return;

    setMessages((prev) => [...prev, { role: 'user', text: prompt }]);
    setInput('');
    setIsSending(true);

    try {
      const result = await api.askGemini(prompt);
      if (result?.response) {
        setMessages((prev) => [...prev, { role: 'gemini', text: result.response }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'gemini', text: result?.error || 'Erro ao comunicar com Gemini.' },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'gemini', text: 'Erro ao enviar mensagem. Verifique conexão.' },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col border-l border-white/[0.06] bg-slate-950/90 backdrop-blur-xl transition-all duration-300 ${
        isOpen ? 'w-[22rem]' : 'w-12'
      }`}
    >
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="absolute -left-3 top-5 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-slate-900 text-slate-400 shadow-lg transition-colors hover:bg-slate-800 hover:text-slate-200"
        title={isOpen ? 'Recolher Gemini' : 'Abrir Gemini'}
      >
        <ChevronRight className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <div className={`flex h-full min-h-0 flex-col ${isOpen ? 'p-4' : 'p-2'}`}>
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300 ring-1 ring-violet-500/20">
            <Sparkles className="h-4 w-4" />
          </div>
          {isOpen && (
            <div>
              <div className="text-sm font-semibold text-slate-100">Gemini</div>
              <div className="text-[11px] text-slate-500">Canal direto de conversa</div>
            </div>
          )}
        </div>

        {isOpen && (
          <>
            <div
              ref={chatContainerRef}
              className="mb-4 flex-1 overflow-y-auto rounded-2xl border border-white/5 bg-slate-900/50 p-3 space-y-3"
            >
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                      msg.role === 'user'
                        ? 'rounded-tr-none bg-violet-600/80 text-white'
                        : 'rounded-tl-none border border-[#4a5851] bg-[#37423d] text-[#e0e8e4]'
                    }`}
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
              {isSending && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] animate-pulse rounded-2xl rounded-tl-none bg-slate-800/50 px-3 py-2 text-sm text-slate-400">
                    Gemini está pensando...
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Digite sua mensagem..."
                disabled={isSending}
                className="min-w-0 flex-1 rounded-xl border border-white/10 bg-slate-900/50 px-3 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-violet-500/50 focus:bg-slate-900/80"
              />
              <button
                type="submit"
                disabled={isSending || !input.trim()}
                className="inline-flex items-center justify-center rounded-xl bg-violet-600 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:bg-slate-800 disabled:text-slate-500"
              >
                <SendHorizontal className="h-4 w-4" />
              </button>
            </form>
          </>
        )}
      </div>
    </aside>
  );
}
