import { create } from 'zustand';

export interface Mensagem {
  role: 'user' | 'assistant';
  content: string;
}

interface AnalysisAIState {
  mensagens: Mensagem[];
  loading: boolean;
  error: string | null;
  setMensagens: (mensagens: Mensagem[]) => void;
  addMensagem: (mensagem: Mensagem) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearMensagens: () => void;
}

export const useAnalysisAIStore = create<AnalysisAIState>((set) => ({
  mensagens: [],
  loading: false,
  error: null,
  setMensagens: (mensagens) => set({ mensagens }),
  addMensagem: (mensagem) => set((state) => ({ mensagens: [...state.mensagens, mensagem] })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearMensagens: () => set({ mensagens: [], error: null }),
}));
