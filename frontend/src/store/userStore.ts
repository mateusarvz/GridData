import { create } from 'zustand';

interface UserState {
  userId: string | null;
  nomeUsuario: string;
  email: string;
  setUser: (userId: string, nomeUsuario: string, email: string) => void;
  clearUser: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  userId: null,
  nomeUsuario: '',
  email: '',
  setUser: (userId, nomeUsuario, email) => set({ userId, nomeUsuario, email }),
  clearUser: () => set({ userId: null, nomeUsuario: '', email: '' }),
}));
