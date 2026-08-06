import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const API_URL = import.meta.env.VITE_API_URL || '';

export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null;

// Login com Google OAuth via Supabase
export async function signInWithGoogle() {
  if (!supabase) {
    return { ok: false, error: 'Login com Google indisponível: Supabase não configurado no frontend.' };
  }

  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: window.location.origin,
    },
  });

  if (error) {
    return { ok: false, error: error.message };
  }
  return { ok: true };
}

// Verifica se há sessão ativa do Supabase (após redirect do Google)
export async function getGoogleSession() {
  if (!supabase) {
    return { ok: false, error: 'Variáveis VITE_SUPABASE_URL/VITE_SUPABASE_ANON_KEY ausentes.' };
  }

  const { data, error } = await supabase.auth.getSession();
  if (error) {
    return { ok: false, error: error.message };
  }

  if (!data.session) {
    return { ok: false, error: 'Nenhuma sessão ativa.' };
  }

  return {
    ok: true,
    email: data.session.user.email || '',
    authUserId: data.session.user.id,
    accessToken: data.session.access_token,
  };
}

// Processa o callback do Google no backend (verifica se existe em public.users)
export async function handleGoogleCallback(accessToken: string) {
  try {
    const res = await fetch(`${API_URL}/api/v1/supabase/google/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ access_token: accessToken }),
    });

    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao conectar ao servidor.' };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Erro ao processar login com Google.' };
    }

    if (payload.user_exists) {
      return {
        ok: true,
        userExists: true,
        user: {
          id: payload.user_id,
          nome_usuario: payload.nome_usuario,
          email: payload.email,
        },
        accessToken: payload.access_token || null,
        refreshToken: payload.refresh_token || null,
      };
    }

    return {
      ok: true,
      userExists: false,
      email: payload.email,
      accessToken: payload.access_token || null,
      refreshToken: payload.refresh_token || null,
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido.' };
  }
}

export async function getSupabaseStatus() {
  try {
    const res = await fetch(`${API_URL}/api/v1/supabase/health`, {
      headers: {
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao consultar health do Supabase.' };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Supabase indisponível.' };
    }

    return { ok: true, message: payload.message || 'Conexão Supabase ativa.' };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido' };
  }
}

// Login: apenas email + senha
export async function authenticateUser(email: string, password: string) {
  try {
    const res = await fetch(`${API_URL}/api/v1/supabase/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, senha: password }),
    });

    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao conectar ao servidor.' };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Email ou senha inválidos.' };
    }

    // Verificar se usuário existe em users
    if (payload.user_exists) {
      return {
        ok: true,
        userExists: true,
        user: {
          id: payload.user_id,
          nome_usuario: payload.nome_usuario,
          email: payload.email,
        },
        accessToken: payload.access_token || null,
        refreshToken: payload.refresh_token || null,
      };
    } else {
      return {
        ok: true,
        userExists: false,
        email: payload.email,
        accessToken: payload.access_token || null,
        refreshToken: payload.refresh_token || null,
      };
    }
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido.' };
  }
}

// Completar perfil: criar em users + user_subscriptions
export async function createUserProfile(
  email: string,
  nome_usuario: string,
  authUserId?: string
) {
  try {
    const res = await fetch(`${API_URL}/api/v1/supabase/create-profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        nome_usuario,
        auth_user_id: authUserId || null,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao criar perfil.' };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Erro ao criar perfil.' };
    }

    return {
      ok: true,
      user: {
        id: payload.user_id,
        nome_usuario: payload.nome_usuario,
        email: payload.email,
      },
      accessToken: payload.access_token || null,
      refreshToken: payload.refresh_token || null,
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido.' };
  }
}

export async function getSubscriptionPlans() {
  try {
    const res = await fetch(`${API_URL}/api/v1/supabase/plans`);
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao buscar planos.', plans: [] };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Erro ao buscar planos.', plans: [] };
    }

    return { ok: true, plans: payload.plans || [] };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido.', plans: [] };
  }
}
