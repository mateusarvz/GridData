import { create } from 'zustand';
import type { UploadedTableMeta } from '../types/dataUpload';

interface DataSessionState {
  tables: UploadedTableMeta[];
  setTables: (tables: UploadedTableMeta[]) => void;
  clearTables: () => void;
}

export const useDataSessionStore = create<DataSessionState>((set) => ({
  tables: [],
  setTables: (tables) => set({ tables }),
  clearTables: () => set({ tables: [] }),
}));
