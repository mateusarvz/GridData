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
          maxWidth: '480px',
          padding: '32px',
          borderRadius: '24px',
          background: 'rgba(15, 23, 42, 0.82)',
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: '0 24px 60px rgba(0, 0, 0, 0.3)',
          backdropFilter: 'blur(18px)',
        }}
      >
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>Complete seu Perfil</h1>
        <p style={{ marginTop: '8px', color: '#cbd5e1' }}>Insira um nome de usuário para ativar sua conta.</p>

        <form onSubmit={handleSubmit} style={{ marginTop: '24px', display: 'grid', gap: '16px' }}>
          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
              Email
            </label>
            <div style={{ ...inputStyle, background: 'rgba(255,255,255,0.05)', color: '#94a3b8', lineHeight: '40px' }}>
              {email}
            </div>
          </div>

          <div>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
              Nome de Usuário
            </label>
            <input
              value={nomeUsuario}
              onChange={(event) => setNomeUsuario(event.target.value)}
              placeholder="Seu nome de usuário"
              autoComplete="username"
              style={inputStyle}
            />
          </div>

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
              marginTop: '8px',
            }}
          >
            {isSubmitting ? 'Criando perfil...' : 'Finalizar cadastro'}
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
  fontSize: '14px',
};

const errorStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: '10px',
  background: 'rgba(239, 68, 68, 0.15)',
  color: '#fca5a5',
  fontSize: '14px',
};
