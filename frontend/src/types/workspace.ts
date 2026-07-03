export type ItemType = 'folder' | 'table';

export interface Position {
  x: number;
  y: number;
}

export interface WorkspaceItem {
  id: string;
  type: ItemType;
  name: string;
  parentId: string | null;
  createdAt: Date;
  updatedAt: Date;
  /** Free-position on the canvas per parent scope */
  position: Position;
  description?: string;
}

export interface FolderItem extends WorkspaceItem {
  type: 'folder';
}

export interface TableItem extends WorkspaceItem {
  type: 'table';
  columnCount: number;
}

export type AnyItem = FolderItem | TableItem;

export interface FolderCounts {
  folders: number;
  tables: number;
}
