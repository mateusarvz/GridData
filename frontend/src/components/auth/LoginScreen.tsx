import { useState } from 'react';
import { authenticateUser, signInWithGoogle } from '../../services/supabase';

interface LoginScreenProps {
  onLogin: (name: string, userId: string, email: string) => void;
  onNeedProfile: (email: string) => void;
}

export function LoginScreen({ onLogin, onNeedProfile }: LoginScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setIsGoogleLoading(true);
    setError('');

    const result = await signInWithGoogle();

    if (!result.ok) {
      setError(result.error || 'Erro ao entrar com Google');
      setIsGoogleLoading(false);
      return;
    }

    // O navegador será redirecionado para o Google.
    // Após o retorno, o App.tsx detecta a sessão e continua o fluxo.
  };

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
      if (result.accessToken) {
        localStorage.setItem('damabox_token', result.accessToken);
      }
      setIsSubmitting(false);
      onLogin(result.user.nome_usuario, result.user.id, trimmedEmail);
    } else {
      if (result.accessToken) {
        localStorage.setItem('damabox_token', result.accessToken);
      }
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

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-700/50" />
          <span className="text-xs text-slate-500">ou</span>
          <div className="h-px flex-1 bg-slate-700/50" />
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isGoogleLoading}
          className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-700/50 bg-white/[0.04] px-4 py-3 text-sm font-semibold text-slate-100 transition hover:bg-white/[0.08] disabled:cursor-wait disabled:opacity-50"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          {isGoogleLoading ? 'Redirecionando...' : 'Login com Google'}
        </button>
      </div>
    </div>
  );
}
