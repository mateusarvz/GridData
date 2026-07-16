import { useEffect, useRef, useState } from 'react';
import { LogOut, CircleDot } from 'lucide-react';
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

  // Initials for avatar
  const initials = (nomeUsuario || 'U')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-slate-950/95 backdrop-blur-xl">
      <div className="flex h-12 w-full items-center justify-between px-5 text-white">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 text-[10px] font-black tracking-tight text-white shadow-lg shadow-violet-500/20">
            D
          </div>
          <span className="text-sm font-bold tracking-[0.08em] text-slate-200">
            DAMABOX
          </span>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* Gemini status */}
          <div
            className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-semibold transition-colors duration-300 ${
              geminiConnected
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400/80'
                : 'border-rose-500/20 bg-rose-500/10 text-rose-400/80'
            }`}
          >
            <CircleDot className={`h-2.5 w-2.5 ${geminiConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
            <span>GEMINI {geminiConnected ? 'ON' : 'OFF'}</span>
          </div>

          {/* User avatar + menu */}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((value) => !value)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-500/20 to-indigo-500/20 text-xs font-bold text-violet-300 ring-1 ring-white/10 transition-all hover:ring-violet-500/30"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              title={nomeUsuario || 'Usuário'}
            >
              {initials}
            </button>

            {menuOpen && (
              <div className="animate-scale-up absolute right-0 mt-2 w-48 overflow-hidden rounded-xl border border-white/10 bg-slate-950/98 shadow-2xl shadow-black/40">
                {/* User info */}
                <div className="border-b border-white/[0.06] px-4 py-3">
                  <div className="text-sm font-medium text-slate-200">{nomeUsuario || 'Usuário'}</div>
                  <div className="mt-0.5 text-[11px] text-slate-500">Logado</div>
                </div>

                {/* Logout */}
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-rose-300/80 transition hover:bg-white/5 hover:text-rose-200"
                >
                  <LogOut className="h-3.5 w-3.5" />
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
