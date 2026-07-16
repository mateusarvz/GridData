import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut } from 'lucide-react';
import { useUserStore } from '../../store/userStore';
import { api } from '../../services/api';

interface TopbarProps {
  onLogout: () => void;
}

export function Topbar({ onLogout }: TopbarProps) {
  const nomeUsuario = useUserStore((state) => state.nomeUsuario);
  const userId = useUserStore((state) => state.userId);
  const [geminiConnected, setGeminiConnected] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (userId) {
      api.checkGeminiStatus().then((status) => {
        setGeminiConnected(!!status?.connected);
      });
    } else {
      setGeminiConnected(false);
    }
  }, [userId]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    setMenuOpen(false);
    onLogout();
  };

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

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((value) => !value)}
              className="flex items-center gap-1 rounded-md px-1.5 py-1 text-base font-semibold uppercase tracking-[0.15em] text-violet-300 transition hover:text-violet-200"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span>damabox</span>
              <ChevronDown className="h-3.5 w-3.5 opacity-60" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 mt-2 w-44 overflow-hidden rounded-2xl border border-white/10 bg-slate-950/98 shadow-2xl shadow-black/30">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-rose-200 transition hover:bg-white/5 hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                  Sair
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
