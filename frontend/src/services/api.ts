// Cliente de API HTTP para o backend Dama Box com suporte a Modo Demo/Offline automático
import type { AnyItem, TableItem } from '../types/workspace';

export interface RowData {
  id: string;
  table_id: string;
  data: Record<string, any>;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface AuditLogItem {
  id: string;
  row_id: string;
  table_id: string;
  user_id: string;
  action: string;
  version: number;
  diff: Record<string, { old: any; new: any }>;
  created_at: string;
}

const API_HOST = import.meta.env.VITE_API_URL || '';

class ApiService {
  private baseUrl = `${API_HOST}/api/v1`;
  public isOnline = false;
  private token: string | null = null;

  constructor() {
    // Tentar carregar token opcional
    this.token = localStorage.getItem('damabox_token') || 'demo-token-12345';
  }

  public async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${API_HOST}/health`, { method: 'GET', headers: this.getHeaders(), signal: AbortSignal.timeout(2500) });
      this.isOnline = res.ok;
      return this.isOnline;
    } catch {
      this.isOnline = false;
      return false;
    }
  }

  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
    };
  }

  // ── Catalog Endpoints ──

  public async listWorkspaceItems(workspaceId: string): Promise<AnyItem[] | null> {
    if (!this.isOnline) return null;
    try {
      const res = await fetch(`${this.baseUrl}/catalog/workspaces/${workspaceId}/items`, {
        headers: this.getHeaders(),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  public async createTable(workspaceId: string, name: string, columns: any[]): Promise<TableItem | null> {
    if (!this.isOnline) return null;
    try {
      const res = await fetch(`${this.baseUrl}/catalog/workspaces/${workspaceId}/tables`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ name, columns }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  // ── Engine Endpoints (Rows & Cells) ──

  public async queryRows(tableId: string): Promise<RowData[]> {
    if (!this.isOnline) return [];
    try {
      const res = await fetch(`${this.baseUrl}/engine/tables/${tableId}/rows/query`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ limit: 100, offset: 0, filters: [] }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.items || [];
    } catch {
      return [];
    }
  }

  public async createRow(tableId: string, data: Record<string, any>): Promise<RowData | null> {
    if (!this.isOnline) return null;
    try {
      const res = await fetch(`${this.baseUrl}/engine/tables/${tableId}/rows`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ data }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  public async updateRow(rowId: string, new_data: Record<string, any>): Promise<RowData | null> {
    if (!this.isOnline) return null;
    try {
      // Usar a rota de Audit inline-edit para que o log seja gerado no backend!
      const res = await fetch(`${this.baseUrl}/audit/rows/${rowId}/inline-edit`, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify({ new_data }),
      });
      if (!res.ok) {
        // Fallback para patch regular
        const res2 = await fetch(`${this.baseUrl}/engine/rows/${rowId}`, {
          method: 'PATCH',
          headers: this.getHeaders(),
          body: JSON.stringify({ data: new_data }),
        });
        if (!res2.ok) return null;
        return await res2.json();
      }
      return await res.json();
    } catch {
      return null;
    }
  }

  // ── Audit & Time Travel Endpoints ──

  public async getRowHistory(rowId: string): Promise<AuditLogItem[]> {
    if (!this.isOnline) return [];
    try {
      const res = await fetch(`${this.baseUrl}/audit/rows/${rowId}/history`, {
        headers: this.getHeaders(),
      });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }

  public async revertRow(rowId: string, targetVersion: number): Promise<RowData | null> {
    if (!this.isOnline) return null;
    try {
      const res = await fetch(`${this.baseUrl}/audit/rows/${rowId}/revert`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ target_version: targetVersion }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  public async checkGeminiStatus(): Promise<{ connected: boolean; api_name: string; error?: string } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/gemini/status`, {
        headers: this.getHeaders(),
      });
      if (!res.ok) return null;
      this.isOnline = true;
      return await res.json();
    } catch {
      return null;
    }
  }

  public async askGemini(prompt: string): Promise<{ response: string; error?: string } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/gemini/chat`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }
}

export const api = new ApiService();
