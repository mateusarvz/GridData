import { useState } from 'react';
import { authenticateUserMain } from '../../services/supabase';

interface LoginScreenProps {
  onLogin: (name: string, userId: string) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();

    if (!trimmedName || !trimmedEmail || !trimmedPassword) {
      setError('Preencha nome, e-mail e senha para entrar.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setError('Informe um e-mail válido.');
      return;
    }

    if (trimmedPassword.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    const result = await authenticateUserMain(trimmedName, trimmedEmail, trimmedPassword);

    if (!result.ok || !result.user) {
      setError(result.error || 'Usuario não encontrado');
      setIsSubmitting(false);
      return;
    }

    localStorage.setItem(
      'dama-box-auth',
      JSON.stringify({
        id: result.user.id,
        name: result.user.name,
        email: result.user.email,
        loggedIn: true,
        loggedAt: new Date().toISOString(),
      })
    );

    setIsSubmitting(false);
    onLogin(result.user.name, result.user.id);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #020617 0%, #111827 100%)',
        color: '#f8fafc',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '420px',
          padding: '32px',
          borderRadius: '24px',
          background: 'rgba(15, 23, 42, 0.82)',
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>Dama Box</h1>
        <p style={{ marginTop: '8px', color: '#cbd5e1' }}>Entre para acessar o workspace.</p>

        <form onSubmit={handleSubmit} style={{ marginTop: '24px', display: 'grid', gap: '14px' }}>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Nome"
            autoComplete="name"
            style={inputStyle}
          />
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="E-mail"
            type="email"
            autoComplete="email"
            style={inputStyle}
          />
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Senha"
            type="password"
            autoComplete="current-password"
            style={inputStyle}
          />

          {error ? <div style={errorStyle}>{error}</div> : null}

          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              padding: '12px 16px',
              borderRadius: '12px',
              border: 'none',
              cursor: isSubmitting ? 'wait' : 'pointer',
              fontWeight: 700,
              background: isSubmitting ? '#475569' : 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
              color: '#fff',
            }}
          >
            {isSubmitting ? 'Validando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: '12px',
  border: '1px solid rgba(148, 163, 184, 0.45)',
  background: 'rgba(255,255,255,0.08)',
  color: '#f8fafc',
  outline: 'none',
};

const errorStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: '10px',
  background: 'rgba(248, 113, 113, 0.16)',
  color: '#fecaca',
  fontSize: '13px',
};
