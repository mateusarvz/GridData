import { useState, useRef, useEffect } from 'react';
import { api } from '../../services/api';

interface Message {
  role: 'user' | 'gemini';
  text: string;
}

export function GeminiChatView() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'gemini', text: 'Olá! Como posso te ajudar hoje?' },
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt) return;

    setMessages((prev) => [...prev, { role: 'user', text: prompt }]);
    setInput('');
    setIsSending(true);

    try {
      const result = await api.askGemini(prompt);
      if (result && result.response) {
        setMessages((prev) => [...prev, { role: 'gemini', text: result.response }]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'gemini', text: result?.error || 'Desculpe, ocorreu um erro ao se comunicar com o Gemini.' },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'gemini', text: 'Erro ao enviar a mensagem. Verifique sua conexão.' },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-9rem)] min-h-[400px]">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-slate-100">Conversar com Gemini</h2>
      </div>

      {/* Chat Area */}
      <div
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto mb-4 p-4 rounded-2xl border border-white/5 bg-slate-950/40 space-y-4"
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${msg.role === 'user'
                ? 'bg-violet-600/80 text-white rounded-tr-none'
                : 'bg-[#37423d] text-[#e0e8e4] border border-[#4a5851] rounded-tl-none'
                }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        {isSending && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl px-4 py-2.5 text-sm bg-slate-800/50 text-slate-400 rounded-tl-none animate-pulse">
              Gemini está pensando...
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Digite sua mensagem..."
          disabled={isSending}
          className="flex-1 rounded-xl border border-white/10 bg-slate-900/50 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-violet-500/50 focus:bg-slate-900/80"
        />
        <button
          type="submit"
          disabled={isSending || !input.trim()}
          className="rounded-xl bg-violet-600 px-6 py-3 text-sm font-semibold text-white hover:bg-violet-500 disabled:bg-slate-800 disabled:text-slate-500 transition-colors"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
