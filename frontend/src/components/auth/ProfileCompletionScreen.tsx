import { useState } from 'react';
import { createUserProfile } from '../../services/supabase';

interface ProfileCompletionScreenProps {
  email: string;
  onProfileComplete: (name: string, userId: string) => void;
}

export function ProfileCompletionScreen({
  email,
  onProfileComplete,
}: ProfileCompletionScreenProps) {
  const [nomeUsuario, setNomeUsuario] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmedNome = nomeUsuario.trim();

    if (!trimmedNome) {
      setError('Digite seu nome de usuário.');
      return;
    }

    if (trimmedNome.length < 3) {
      setError('Nome de usuário deve ter pelo menos 3 caracteres.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    const result = await createUserProfile(email, trimmedNome);

    if (!result.ok || !result.user) {
      setError(result.error || 'Erro ao criar perfil');
      setIsSubmitting(false);
      return;
    }

    if (result.accessToken) {
      localStorage.setItem('damabox_token', result.accessToken);
    }

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
    onProfileComplete(result.user.nome_usuario, result.user.id);
  };

  return (
    <div className="auth-bg flex min-h-screen items-center justify-center p-6">
      <div className="auth-grid fixed inset-0" />

      <div className="animate-fade-in relative z-10 w-full max-w-[480px] rounded-3xl border border-white/[0.08] bg-slate-950/70 p-8 shadow-2xl shadow-black/40 backdrop-blur-2xl">
        {/* Logo */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-black text-white shadow-lg shadow-violet-500/25">
            D
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Complete seu Perfil</h1>
            <p className="text-xs text-slate-500">Insira um nome de usuário</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-4">
          {/* Email (readonly) */}
          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Email
            </label>
            <div className="rounded-xl border border-slate-700/30 bg-white/[0.02] px-4 py-3 text-sm text-slate-500">
              {email}
            </div>
          </div>

          {/* Username */}
          <div>
            <label className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Nome de Usuário
            </label>
            <input
              value={nomeUsuario}
              onChange={(event) => setNomeUsuario(event.target.value)}
              placeholder="Seu nome de usuário"
              autoComplete="username"
              className="w-full rounded-xl border border-slate-700/50 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none transition focus:border-violet-500/40 focus:bg-white/[0.06]"
            />
          </div>

          {error ? (
            <div className="rounded-xl bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-1 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-violet-500/20 transition-all hover:shadow-violet-500/30 disabled:cursor-wait disabled:opacity-50"
          >
            {isSubmitting ? 'Criando perfil...' : 'Finalizar cadastro'}
          </button>
        </form>
      </div>
    </div>
  );
}
