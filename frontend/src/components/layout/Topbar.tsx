import { useEffect, useState } from 'react';
import { useUserStore } from '../../store/userStore';
import { api } from '../../services/api';

export function Topbar() {
  const nomeUsuario = useUserStore((state) => state.nomeUsuario);
  const userId = useUserStore((state) => state.userId);
  const [geminiConnected, setGeminiConnected] = useState(false);

  useEffect(() => {
    if (userId) {
      api.checkGeminiStatus().then((status) => {
        if (status && status.connected) {
          setGeminiConnected(true);
        } else {
          setGeminiConnected(false);
        }
      });
    } else {
      setGeminiConnected(false);
    }
  }, [userId]);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/95 backdrop-blur-xl">
      <div className="flex w-full items-center justify-between px-8 py-4 text-white">
        <div className="text-sm text-slate-300">{nomeUsuario || 'Usuário'}</div>
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition-colors duration-300 ${
              geminiConnected
                ? 'border-[#4a5851] bg-[#2d3832] text-[#8ea397]'
                : 'border-[#574a4a] bg-[#382d2d] text-[#a38e8e]'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${geminiConnected ? 'bg-[#7ba38a]' : 'bg-[#a37b7b]'}`} />
            <span>GEMINI {geminiConnected ? 'CONECTADO' : 'DESCONECTADO'}</span>
          </div>
          <div className="text-base font-semibold uppercase tracking-[0.15em] text-violet-300">damabox</div>
        </div>
      </div>
    </header>
  );
}
