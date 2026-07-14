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
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #020617 0%, #111827 100%)', color: '#f8fafc', padding: '24px' }}>
      <div style={{ width: '100%', maxWidth: '420px', padding: '32px', borderRadius: '24px', background: 'rgba(15, 23, 42, 0.82)', border: '1px solid rgba(255,255,255,0.12)', boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)', backdropFilter: 'blur(18px)' }}>
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>Dama Box</h1>
        <p style={{ marginTop: '8px', color: '#cbd5e1' }}>Entre com seu email e senha.</p>

        <form onSubmit={handleSubmit} style={{ marginTop: '24px', display: 'grid', gap: '14px' }}>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" autoComplete="email" style={inputStyle} />
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Senha" type="password" autoComplete="current-password" style={inputStyle} />
          {error && <div style={errorStyle}>{error}</div>}
          <button type="submit" disabled={isSubmitting} style={{ padding: '12px 16px', borderRadius: '12px', border: 'none', cursor: isSubmitting ? 'wait' : 'pointer', fontWeight: 700, background: isSubmitting ? '#475569' : 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)', color: '#fff' }}>
            {isSubmitting ? 'Validando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = { width: '100%', padding: '12px 14px', borderRadius: '12px', border: '1px solid rgba(148, 163, 184, 0.45)', background: 'rgba(255,255,255,0.08)', color: '#f8fafc', outline: 'none' };
const errorStyle: React.CSSProperties = { padding: '10px 12px', borderRadius: '10px', background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', fontSize: '14px' };
