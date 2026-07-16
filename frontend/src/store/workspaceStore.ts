import { create } from 'zustand';
import type { AnyItem, ItemType, FolderCounts, Position } from '../types/workspace';
import { api } from '../services/api';
import type { WorkspaceTreeItemDTO } from '../services/api';

// Spread initial positions so items don't overlap
function spreadPos(index: number): Position {
  const cols = 4;
  const col = index % cols;
  const row = Math.floor(index / cols);
  return { x: 32 + col * 300, y: 32 + row * 200 };
}

interface WorkspaceState {
  items: AnyItem[];
  currentFolderId: string | null;
  breadcrumb: { id: string | null; name: string }[];
  isOnline: boolean;
  isLoading: boolean;
  activeWorkspaceId: string | null;

  checkApiStatus: () => Promise<void>;
  fetchTree: (workspaceId: string) => Promise<void>;
  getChildCounts: (folderId: string) => FolderCounts;
  navigateTo: (folderId: string | null) => void;
  createItem: (type: ItemType, name: string, pos: Position, parentId?: string | null) => Promise<void>;
  renameItem: (id: string, name: string) => Promise<void>;
  deleteItem: (id: string) => Promise<void>;
  moveItem: (id: string, newParentId: string | null) => Promise<void>;
  setPosition: (id: string, pos: Position) => void;
  setActiveWorkspace: (workspaceId: string) => void;
}

function treeItemToAnyItem(dto: WorkspaceTreeItemDTO, index: number): AnyItem {
  const base = {
    id: dto.id,
    name: dto.name,
    parentId: dto.parent_id,
    createdAt: new Date(dto.created_at),
    updatedAt: new Date(dto.updated_at),
    position: spreadPos(index),
  };

  if (dto.type === 'folder') {
    return { ...base, type: 'folder' as const };
  }
  return {
    ...base,
    type: 'table' as const,
    description: dto.column_count ? `${dto.column_count} colunas definidas` : 'Vazia · 0 colunas',
    columnCount: dto.column_count ?? 0,
  };
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  items: [],
  currentFolderId: null,
  breadcrumb: [{ id: null, name: 'Workspace' }],
  isOnline: false,
  isLoading: false,
  activeWorkspaceId: null,

  checkApiStatus: async () => {
    const online = await api.checkHealth();
    set({ isOnline: online });
  },

  setActiveWorkspace: (workspaceId: string) => {
    set({ activeWorkspaceId: workspaceId });
  },

  fetchTree: async (workspaceId: string) => {
    set({ isLoading: true, activeWorkspaceId: workspaceId });
    try {
      const tree = await api.listWorkspaceTree(workspaceId);

      // Compute positions per parent group
      const parentGroups = new Map<string | null, number>();
      const items: AnyItem[] = tree.map((dto) => {
        const parentKey = dto.parent_id;
        const idx = parentGroups.get(parentKey) ?? 0;
        parentGroups.set(parentKey, idx + 1);
        return treeItemToAnyItem(dto, idx);
      });

      set({ items, isLoading: false });
    } catch {
      set({ items: [], isLoading: false });
    }
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

  createItem: async (type, name, pos, parentId) => {
    const { activeWorkspaceId, currentFolderId } = get();
    if (!activeWorkspaceId) return;

    const targetParent = parentId !== undefined ? parentId : currentFolderId;

    if (type === 'folder') {
      const result = await api.createFolder(activeWorkspaceId, name, targetParent);
      if (result) {
        const newItem: AnyItem = {
          id: result.id,
          type: 'folder',
          name: result.name,
          parentId: result.parent_id,
          createdAt: new Date(),
          updatedAt: new Date(),
          position: pos,
        };
        set((s) => ({ items: [...s.items, newItem] }));
      }
    } else {
      const result = await api.createTable(activeWorkspaceId, name, targetParent);
      if (result) {
        const newItem: AnyItem = {
          id: result.id,
          type: 'table',
          name: result.name,
          parentId: result.folder_id,
          createdAt: new Date(),
          updatedAt: new Date(),
          position: pos,
          description: 'Vazia · 0 colunas',
          columnCount: 0,
        };
        set((s) => ({ items: [...s.items, newItem] }));
      }
    }
  },

  renameItem: async (id, name) => {
    const item = get().items.find((i) => i.id === id);
    if (!item) return;

    let ok = false;
    if (item.type === 'folder') {
      const result = await api.renameFolder(id, name);
      ok = result !== null;
    } else {
      const result = await api.renameTable(id, name);
      ok = result !== null;
    }

    if (ok) {
      set((s) => ({
        items: s.items.map((i) => i.id === id ? { ...i, name, updatedAt: new Date() } : i),
      }));
    }
  },

  deleteItem: async (id) => {
    const item = get().items.find((i) => i.id === id);
    if (!item) return;

    let ok = false;
    if (item.type === 'folder') {
      ok = await api.deleteFolder(id);
    } else {
      ok = await api.deleteTable(id);
    }

    if (ok) {
      // Remove item and all descendants (for folders)
      const toDelete = new Set<string>();
      const collect = (pid: string) => {
        toDelete.add(pid);
        get().items.filter((i) => i.parentId === pid).forEach((c) => collect(c.id));
      };
      collect(id);
      set((s) => ({ items: s.items.filter((i) => !toDelete.has(i.id)) }));
    }
  },

  moveItem: async (id, newParentId) => {
    if (id === newParentId) return;
    const { items } = get();
    const item = items.find((i) => i.id === id);
    if (!item) return;

    // Prevent circular moves (folder into its own descendant)
    const isDesc = (pid: string | null, targetId: string): boolean => {
      if (!pid) return false;
      if (pid === targetId) return true;
      const p = items.find((i) => i.id === pid);
      return p ? isDesc(p.parentId, targetId) : false;
    };
    if (newParentId && isDesc(newParentId, id)) return;

    let ok = false;
    if (item.type === 'folder') {
      const result = await api.moveFolder(id, newParentId);
      ok = result !== null;
    } else {
      const result = await api.moveTable(id, newParentId);
      ok = result !== null;
    }

    if (ok) {
      // Count siblings in new parent to assign spread position
      const siblings = items.filter((i) => i.id !== id && i.parentId === newParentId);
      const newPos = spreadPos(siblings.length);

      set((s) => ({
        items: s.items.map((i) =>
          i.id === id ? { ...i, parentId: newParentId, position: newPos, updatedAt: new Date() } : i
        ),
      }));
    }
  },

  setPosition: (id, pos) => {
    set((s) => ({
      items: s.items.map((i) => i.id === id ? { ...i, position: pos } : i),
    }));
  },
}));
