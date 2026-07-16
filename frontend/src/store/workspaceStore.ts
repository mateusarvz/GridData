import { create } from 'zustand';
import type { AnyItem, ItemType, FolderCounts, Position } from '../types/workspace';
import { api } from '../services/api';

let _nextId = 100;
const uid = () => `item-${_nextId++}`;
const now = () => new Date();

// Spread initial positions so items don't overlap
function spreadPos(index: number): Position {
  const cols = 4;
  const col = index % cols;
  const row = Math.floor(index / cols);
  return { x: 32 + col * 300, y: 32 + row * 200 };
}

function createMockData(): AnyItem[] {
  const items: AnyItem[] = [
    {
      id: 'f-fin', type: 'folder', name: 'Gestão Financeira',
      parentId: null, createdAt: new Date('2026-05-10'), updatedAt: new Date('2026-06-20'),
      position: spreadPos(0),
    },
    {
      id: 'f-rh', type: 'folder', name: 'Recursos Humanos',
      parentId: null, createdAt: new Date('2026-04-01'), updatedAt: new Date('2026-06-25'),
      position: spreadPos(1),
    },
    {
      id: 't-clientes', type: 'table', name: 'Clientes Ativos',
      parentId: null, createdAt: new Date('2026-03-20'), updatedAt: new Date('2026-06-28'),
      description: 'Vazia · 0 colunas', columnCount: 0, position: spreadPos(2),
    },
    // inside f-fin
    {
      id: 't-fluxo', type: 'table', name: 'Fluxo de Caixa',
      parentId: 'f-fin', createdAt: new Date('2026-05-12'), updatedAt: new Date('2026-06-18'),
      description: '3 colunas definidas', columnCount: 3, position: spreadPos(0),
    },
    {
      id: 'f-audit', type: 'folder', name: 'Auditoria 2025',
      parentId: 'f-fin', createdAt: new Date('2026-05-15'), updatedAt: new Date('2026-06-01'),
      position: spreadPos(1),
    },
    // inside f-rh
    {
      id: 't-funcs', type: 'table', name: 'Funcionários',
      parentId: 'f-rh', createdAt: new Date('2026-04-02'), updatedAt: new Date('2026-06-24'),
      description: '5 colunas definidas', columnCount: 5, position: spreadPos(0),
    },
    {
      id: 't-folha', type: 'table', name: 'Folha de Pagamento',
      parentId: 'f-rh', createdAt: new Date('2026-04-03'), updatedAt: new Date('2026-06-22'),
      description: '4 colunas definidas', columnCount: 4, position: spreadPos(1),
    },
  ];
  return items;
}

interface WorkspaceState {
  items: AnyItem[];
  currentFolderId: string | null;
  breadcrumb: { id: string | null; name: string }[];
  isOnline: boolean;

  checkApiStatus: () => Promise<void>;
  getChildCounts: (folderId: string) => FolderCounts;
  navigateTo: (folderId: string | null) => void;
  createItem: (type: ItemType, name: string, pos: Position, parentId?: string | null) => void;
  renameItem: (id: string, name: string) => void;
  deleteItem: (id: string) => void;
  moveItem: (id: string, newParentId: string | null) => void;
  setPosition: (id: string, pos: Position) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  items: createMockData(),
  currentFolderId: null,
  breadcrumb: [{ id: null, name: 'Workspace' }],
  isOnline: false,

  checkApiStatus: async () => {
    const online = await api.checkHealth();
    set({ isOnline: online });
  },

  getChildCounts: (folderId) => {
    const children = get().items.filter((i) => i.parentId === folderId);
    return {
      folders: children.filter((i) => i.type === 'folder').length,
      tables: children.filter((i) => i.type === 'table').length,
    };
  },

  navigateTo: (folderId) => {
    const { items } = get();
    const path: { id: string | null; name: string }[] = [{ id: null, name: 'Workspace' }];
    if (folderId !== null) {
      const ancestors: { id: string; name: string }[] = [];
      let current: string | null = folderId;
      while (current) {
        const item = items.find((i) => i.id === current);
        if (!item) break;
        ancestors.unshift({ id: item.id, name: item.name });
        current = item.parentId;
      }
      path.push(...ancestors);
    }
    set({ currentFolderId: folderId, breadcrumb: path });
  },

  createItem: (type, name, pos, parentId) => {
    const targetParent = parentId !== undefined ? parentId : get().currentFolderId;
    const base = { id: uid(), name, parentId: targetParent, createdAt: now(), updatedAt: now(), position: pos };
    const newItem: AnyItem = type === 'folder'
      ? { ...base, type: 'folder' }
      : { ...base, type: 'table', description: 'Vazia · 0 colunas', columnCount: 0 };
    set((s) => ({ items: [...s.items, newItem] }));
  },

  renameItem: (id, name) => {
    set((s) => ({
      items: s.items.map((i) => i.id === id ? { ...i, name, updatedAt: now() } : i),
    }));
  },

  deleteItem: (id) => {
    const toDelete = new Set<string>();
    const collect = (pid: string) => {
      toDelete.add(pid);
      get().items.filter((i) => i.parentId === pid).forEach((c) => collect(c.id));
    };
    collect(id);
    set((s) => ({ items: s.items.filter((i) => !toDelete.has(i.id)) }));
  },

  moveItem: (id, newParentId) => {
    if (id === newParentId) return;
    const { items } = get();
    const isDesc = (pid: string | null, targetId: string): boolean => {
      if (!pid) return false;
      if (pid === targetId) return true;
      const p = items.find((i) => i.id === pid);
      return p ? isDesc(p.parentId, targetId) : false;
    };
    if (newParentId && isDesc(newParentId, id)) return;

    // Count siblings in new parent to assign spread position
    const siblings = items.filter((i) => i.id !== id && i.parentId === newParentId);
    const newPos = spreadPos(siblings.length);

    set((s) => ({
      items: s.items.map((i) =>
        i.id === id ? { ...i, parentId: newParentId, position: newPos, updatedAt: now() } : i
      ),
    }));
  },

  setPosition: (id, pos) => {
    set((s) => ({
      items: s.items.map((i) => i.id === id ? { ...i, position: pos } : i),
    }));
  },
}));
