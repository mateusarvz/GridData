import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null;

export async function getSupabaseStatus() {
  if (!supabase) {
    return { ok: false, error: 'Variáveis VITE_SUPABASE_URL/VITE_SUPABASE_ANON_KEY ausentes.' };
  }

  try {
    const { data, error } = await supabase.from('user_main').select('id').limit(1);
    if (error) {
      return { ok: false, error: error.message };
    }

    return { ok: true, message: 'Conexão Supabase ativa.', count: data?.length ?? 0 };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido' };
  }
}

export async function authenticateUserMain(name: string, email: string, password: string) {
  try {
    const res = await fetch('/api/v1/supabase/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ nome_usuario: name, email, senha: password }),
    });

    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text || 'Erro ao conectar ao servidor.' };
    }

    const payload = await res.json();
    if (!payload.ok) {
      return { ok: false, error: payload.error || 'Usuario não encontrado.' };
    }

    return {
      ok: true,
      user: {
        id: payload.user_id,
        name: payload.nome_usuario,
        email: payload.email,
      },
    };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : 'Erro desconhecido.' };
  }
}
