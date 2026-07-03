import { useState, useMemo, useRef } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { BreadcrumbNav } from './BreadcrumbNav';
import { FloatingDock } from './FloatingDock';
import { FolderCard } from './FolderCard';
import { TableCard } from './TableCard';
import { CreateModal } from './CreateModal';
import { TablePreview } from './TablePreview';
import { EmptyState } from './EmptyState';
import type { ItemType, AnyItem, TableItem, Position } from '../../types/workspace';
import { Folder, Table2 } from 'lucide-react';

// ── Draggable item wrapper ──

interface DraggableItemProps {
  item: AnyItem;
  onOpen: () => void;
  onRename: (name: string) => void;
  onDelete: () => void;
  getChildCounts: (id: string) => { folders: number; tables: number };
}

function DraggableItem({ item, onOpen, onRename, onDelete, getChildCounts }: DraggableItemProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
    data: { type: 'item', item },
  });

  const pos = item.position;
  const cardStyle: React.CSSProperties = {
    position: 'absolute',
    left: pos.x,
    top: pos.y,
    transform: transform ? `translate(${transform.x}px, ${transform.y}px)` : undefined,
    zIndex: isDragging ? 50 : 1,
  };

  if (item.type === 'folder') {
    return (
      <div ref={setNodeRef} style={cardStyle}>
        <FolderCard
          item={item}
          counts={getChildCounts(item.id)}
          onOpen={onOpen}
          onRename={onRename}
          onDelete={onDelete}
          dragListeners={listeners as Record<string, unknown>}
          dragAttributes={attributes as Record<string, unknown>}
          isDragging={isDragging}
        />
      </div>
    );
  }

  return (
    <div ref={setNodeRef} style={cardStyle}>
      <TableCard
        item={item as TableItem}
        onOpen={onOpen}
        onRename={onRename}
        onDelete={onDelete}
        dragListeners={listeners as Record<string, unknown>}
        dragAttributes={attributes as Record<string, unknown>}
        isDragging={isDragging}
      />
    </div>
  );
}

// ── Main canvas ──

export function WorkspaceCanvas() {
  const allItems = useWorkspaceStore((s) => s.items);
  const currentFolderId = useWorkspaceStore((s) => s.currentFolderId);
  const navigateTo = useWorkspaceStore((s) => s.navigateTo);
  const createItem = useWorkspaceStore((s) => s.createItem);
  const renameItem = useWorkspaceStore((s) => s.renameItem);
  const deleteItem = useWorkspaceStore((s) => s.deleteItem);
  const moveItem = useWorkspaceStore((s) => s.moveItem);
  const setPosition = useWorkspaceStore((s) => s.setPosition);
  const getChildCounts = useWorkspaceStore((s) => s.getChildCounts);

  const items = useMemo(
    () => allItems.filter((i) => i.parentId === currentFolderId),
    [allItems, currentFolderId]
  );

  const [createModal, setCreateModal] = useState<{
    type: ItemType;
    pos: Position;
    parentId?: string | null;
  } | null>(null);
  const [previewTable, setPreviewTable] = useState<TableItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeItem, setActiveItem] = useState<AnyItem | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter((i) => i.name.toLowerCase().includes(q));
  }, [items, searchQuery]);

  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current;
    if (data?.type === 'item') setActiveItem(data.item as AnyItem);
    else if (data?.type === 'dock-create') setActiveItem(null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveItem(null);
    const { active, over, delta } = event;
    const activeData = active.data.current;
    const overData = over?.data.current;

    // ── Dock create ──
    if (activeData?.type === 'dock-create') {
      const itemType = activeData.itemType as ItemType;
      // Calculate drop position on canvas
      const canvasRect = canvasRef.current?.getBoundingClientRect();
      const dropPos: Position = canvasRect
        ? {
            x: Math.max(0, (active.rect.current.translated?.left ?? 200) - canvasRect.left),
            y: Math.max(0, (active.rect.current.translated?.top ?? 100) - canvasRect.top - 60),
          }
        : { x: 200, y: 100 };

      if (overData?.type === 'folder-target') {
        setCreateModal({ type: itemType, pos: { x: 32, y: 32 }, parentId: overData.folderId as string });
      } else {
        setCreateModal({ type: itemType, pos: dropPos });
      }
      return;
    }

    // ── Move existing item ──
    if (activeData?.type === 'item') {
      const item = activeData.item as AnyItem;

      if (overData?.type === 'folder-target' && overData.folderId !== item.id) {
        // Drop onto a folder → move inside
        moveItem(item.id, overData.folderId as string);
      } else {
        // Free-position drag — update x,y
        const newPos: Position = {
          x: Math.max(0, item.position.x + delta.x),
          y: Math.max(0, item.position.y + delta.y),
        };
        setPosition(item.id, newPos);
      }
    }
  };

  // Compute canvas height to accommodate all items
  const canvasHeight = useMemo(() => {
    if (filteredItems.length === 0) return 400;
    return Math.max(400, ...filteredItems.map((i) => i.position.y + 220));
  }, [filteredItems]);

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--color-bg)' }}>

        {/* Header */}
        <header className="px-6 pt-5 pb-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <div className="flex items-center gap-3 mb-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              <span className="text-white text-sm font-bold">D</span>
            </div>
            <h1 className="text-lg font-semibold" style={{ color: 'var(--color-ink)' }}>Dama Box</h1>
          </div>
          <BreadcrumbNav />
        </header>

        {/* Canvas area */}
        <main className="flex-1 overflow-auto pb-24">
          <div
            ref={canvasRef}
            className="relative"
            style={{ minHeight: canvasHeight, minWidth: 800 }}
          >
            {filteredItems.length === 0 ? (
              <EmptyState className="absolute inset-0 flex flex-col items-center justify-center" />
            ) : (
              filteredItems.map((item) => (
                <DraggableItem
                  key={item.id}
                  item={item}
                  onOpen={() =>
                    item.type === 'folder'
                      ? navigateTo(item.id)
                      : setPreviewTable(item as TableItem)
                  }
                  onRename={(name) => renameItem(item.id, name)}
                  onDelete={() => deleteItem(item.id)}
                  getChildCounts={getChildCounts}
                />
              ))
            )}
          </div>
        </main>

        {/* Floating Dock */}
        <FloatingDock
          onCreateClick={(type) =>
            setCreateModal({ type, pos: { x: 200 + Math.random() * 200, y: 80 + Math.random() * 200 } })
          }
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        {/* Drag Overlay */}
        <DragOverlay>
          {activeItem && (
            <div
              className="flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium"
              style={{
                backgroundColor: 'var(--color-bg)',
                border: '1px solid var(--color-primary)',
                boxShadow: 'var(--shadow-lg)',
                color: 'var(--color-ink)',
                maxWidth: '240px',
              }}
            >
              {activeItem.type === 'folder'
                ? <Folder size={16} style={{ color: 'var(--color-primary)' }} />
                : <Table2 size={16} style={{ color: 'var(--color-accent)' }} />
              }
              <span className="truncate">{activeItem.name}</span>
            </div>
          )}
        </DragOverlay>

        {/* Create Modal */}
        {createModal && (
          <CreateModal
            type={createModal.type}
            onConfirm={(name) => createItem(createModal.type, name, createModal.pos, createModal.parentId)}
            onClose={() => setCreateModal(null)}
          />
        )}

        {/* Table Preview */}
        {previewTable && (
          <>
            <div
              className="fixed inset-0"
              style={{ zIndex: 'var(--z-modal-backdrop)' as React.CSSProperties['zIndex'], backgroundColor: 'oklch(0.200 0.000 0 / 0.15)' }}
              onClick={() => setPreviewTable(null)}
            />
            <TablePreview item={previewTable} onClose={() => setPreviewTable(null)} />
          </>
        )}
      </div>
    </DndContext>
  );
}
