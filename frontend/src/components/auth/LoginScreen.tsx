import { useState } from 'react';
import { authenticateUser } from '../../services/supabase';

interface LoginScreenProps {
  onLogin: (name: string, userId: string, email: string) => void;
  onNeedProfile: (email: string) => void;
}

export function LoginScreen({ onLogin, onNeedProfile }: LoginScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError('Preencha email e senha para entrar.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Informe um email válido.');
      return;
    }

    if (trimmedPassword.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    const result = await authenticateUser(trimmedEmail, trimmedPassword);

    if (!result.ok) {
      setError(result.error || 'Erro ao fazer login');
      setIsSubmitting(false);
      return;
    }

    if (result.userExists && result.user) {
      localStorage.setItem(
        'dama-box-auth',
        JSON.stringify({
          id: result.user.id,
          nome_usuario: result.user.nome_usuario,
          email: result.user.email,
          loggedIn: true,
          loggedAt: new Date().toISOString(),
        })
      );
      setIsSubmitting(false);
      onLogin(result.user.nome_usuario, result.user.id, trimmedEmail);
    } else {
      setIsSubmitting(false);
      onNeedProfile(result.email || trimmedEmail);
    }
  };

  return (
    <div className="auth-bg flex min-h-screen items-center justify-center p-6">
      <div className="auth-grid fixed inset-0" />

      <div className="animate-fade-in relative z-10 w-full max-w-[420px] rounded-3xl border border-white/[0.08] bg-slate-950/70 p-8 shadow-2xl shadow-black/40 backdrop-blur-2xl">
        {/* Logo */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-black text-white shadow-lg shadow-violet-500/25">
            D
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Dama Box</h1>
            <p className="text-xs text-slate-500">Plataforma de dados</p>
          </div>
        </div>

        <p className="mb-6 text-sm text-slate-400">Entre com seu email e senha.</p>

        <form onSubmit={handleSubmit} className="grid gap-3.5">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            type="email"
            autoComplete="email"
            className="w-full rounded-xl border border-slate-700/50 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none transition focus:border-violet-500/40 focus:bg-white/[0.06]"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Senha"
            type="password"
            autoComplete="current-password"
            className="w-full rounded-xl border border-slate-700/50 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none transition focus:border-violet-500/40 focus:bg-white/[0.06]"
          />

          {error && (
            <div className="rounded-xl bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-violet-500/20 transition-all hover:shadow-violet-500/30 disabled:cursor-wait disabled:opacity-50"
          >
            {isSubmitting ? 'Validando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}
