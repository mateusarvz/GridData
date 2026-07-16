import { useState, useCallback } from 'react';
import { ChevronRight, Folder, FolderOpen, Table2 } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspaceStore';
import type { AnyItem } from '../../types/workspace';

interface TreeNodeProps {
  item: AnyItem;
  allItems: AnyItem[];
  level: number;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
}

function TreeNode({ item, allItems, level, expandedIds, onToggle }: TreeNodeProps) {
  const isFolder = item.type === 'folder';
  const isExpanded = expandedIds.has(item.id);
  const children = allItems.filter((i) => i.parentId === item.id);

  return (
    <div>
      <button
        type="button"
        onClick={() => {
          if (isFolder) onToggle(item.id);
        }}
        className={`tree-item w-full text-left ${isFolder ? '' : 'cursor-default'}`}
        style={{ paddingLeft: `${8 + level * 16}px` }}
        title={item.name}
      >
        {/* Chevron — only for folders */}
        {isFolder ? (
          <ChevronRight
            className={`tree-chevron h-3.5 w-3.5 text-slate-500 ${isExpanded ? 'tree-chevron-open' : ''}`}
          />
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        {/* Icon */}
        {isFolder ? (
          isExpanded ? (
            <FolderOpen className="h-4 w-4 shrink-0 text-amber-400/80" />
          ) : (
            <Folder className="h-4 w-4 shrink-0 text-amber-400/60" />
          )
        ) : (
          <Table2 className="h-4 w-4 shrink-0 text-violet-400/70" />
        )}

        {/* Label */}
        <span className="truncate">{item.name}</span>
      </button>

      {/* Children */}
      {isFolder && isExpanded && children.length > 0 && (
        <div className="tree-children">
          {children.map((child) => (
            <TreeNode
              key={child.id}
              item={child}
              allItems={allItems}
              level={level + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TreeNavigator() {
  const items = useWorkspaceStore((state) => state.items);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const handleToggle = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const rootItems = items.filter((i) => i.parentId === null);

  if (rootItems.length === 0) {
    return (
      <div className="px-3 py-2 text-xs text-slate-500 italic">
        Nenhum item no workspace
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {rootItems.map((item) => (
        <TreeNode
          key={item.id}
          item={item}
          allItems={items}
          level={0}
          expandedIds={expandedIds}
          onToggle={handleToggle}
        />
      ))}
    </div>
  );
}
