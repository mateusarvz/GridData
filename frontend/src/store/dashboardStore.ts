import { create } from 'zustand';

export interface DashboardChart {
  id: string;
  item_type: string;
  title: string;
  description: string;
  chart_type?: string;
  sql?: string;
  image_base64?: string;
  content?: string;
  table_data?: {
    columns: string[];
    rows: Array<Array<string | number | null>>;
    rows_count: number;
  } | null;
  reason?: string;
}

interface DashboardState {
  charts: DashboardChart[];
  loading: boolean;
  error: string | null;
  setCharts: (charts: DashboardChart[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearCharts: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  charts: [],
  loading: false,
  error: null,
  setCharts: (charts) => set({ charts }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearCharts: () => set({ charts: [], error: null }),
}));
