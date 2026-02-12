'use client'

import * as React from 'react'
import { ChevronRight, ChevronDown, Folder, FolderOpen } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { TreeNodeData, TreeViewerProps, TreeNodeRenderProps } from './types'

const DEFAULT_CONFIG = {
  defaultExpandAll: false,
  defaultExpandedIds: [] as string[],
  multiSelect: false,
  showLines: true,
  collapsible: true,
  animationDuration: 150,
  indentSize: 20,
}

/**
 * Default node renderer
 */
function DefaultTreeNode<T extends TreeNodeData>({
  node,
  isExpanded,
  isSelected,
  hasChildren,
  onToggle,
  onSelect,
}: TreeNodeRenderProps<T>) {
  return (
    <div
      className={cn(
        'flex items-center gap-1 py-1 px-2 rounded-md cursor-pointer transition-colors',
        'hover:bg-accent/50',
        isSelected && 'bg-accent text-accent-foreground'
      )}
      onClick={onSelect}
    >
      {/* Expand/Collapse button */}
      {hasChildren ? (
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 p-0"
          onClick={(e) => {
            e.stopPropagation()
            onToggle()
          }}
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </Button>
      ) : (
        <span className="w-5" />
      )}

      {/* Icon */}
      {node.icon || (
        hasChildren ? (
          isExpanded ? (
            <FolderOpen className="h-4 w-4 text-amber-500" />
          ) : (
            <Folder className="h-4 w-4 text-amber-500" />
          )
        ) : (
          <Folder className="h-4 w-4 text-muted-foreground" />
        )
      )}

      {/* Label */}
      <span className="text-sm truncate">{node.label}</span>
    </div>
  )
}

/**
 * Recursive tree node component
 */
function TreeNode<T extends TreeNodeData>({
  node,
  depth,
  expandedIds,
  selectedIds,
  config,
  onToggle,
  onSelect,
  onDoubleClick,
  renderNode,
}: {
  node: T
  depth: number
  expandedIds: Set<string>
  selectedIds: Set<string>
  config: typeof DEFAULT_CONFIG
  onToggle: (id: string) => void
  onSelect: (node: T) => void
  onDoubleClick?: (node: T) => void
  renderNode?: TreeViewerProps<T>['renderNode']
}) {
  const isExpanded = expandedIds.has(node.id)
  const isSelected = selectedIds.has(node.id)
  const hasChildren = (node.children?.length ?? 0) > 0

  const renderProps: TreeNodeRenderProps<T> = {
    node,
    depth,
    isExpanded,
    isSelected,
    hasChildren,
    onToggle: () => onToggle(node.id),
    onSelect: () => onSelect(node),
  }

  const NodeRenderer = renderNode || DefaultTreeNode

  return (
    <div className="relative">
      {/* Connecting lines */}
      {config.showLines && depth > 0 && (
        <div
          className="absolute border-l border-border"
          style={{
            left: `${(depth - 1) * config.indentSize + 10}px`,
            top: 0,
            height: '50%',
          }}
        />
      )}

      {/* Node content */}
      <div
        style={{ paddingLeft: `${depth * config.indentSize}px` }}
        onDoubleClick={onDoubleClick ? () => onDoubleClick(node) : undefined}
      >
        <NodeRenderer {...renderProps} />
      </div>

      {/* Children */}
      {hasChildren && (
        <div
          className={cn(
            'overflow-hidden transition-all',
            config.animationDuration > 0 && 'transition-[max-height,opacity]'
          )}
          style={{
            maxHeight: isExpanded ? '100vh' : '0px',
            opacity: isExpanded ? 1 : 0,
            transitionDuration: `${config.animationDuration}ms`,
          }}
        >
          {node.children?.map((child) => (
            <TreeNode
              key={child.id}
              node={child as T}
              depth={depth + 1}
              expandedIds={expandedIds}
              selectedIds={selectedIds}
              config={config}
              onToggle={onToggle}
              onSelect={onSelect}
              onDoubleClick={onDoubleClick}
              renderNode={renderNode}
            />
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Collect all node IDs from a tree
 */
function collectAllIds<T extends TreeNodeData>(nodes: T[]): string[] {
  const ids: string[] = []
  const traverse = (items: T[]) => {
    for (const item of items) {
      ids.push(item.id)
      if (item.children) {
        traverse(item.children as T[])
      }
    }
  }
  traverse(nodes)
  return ids
}

/**
 * A reusable tree viewer component for displaying hierarchical data.
 * 
 * @example
 * ```tsx
 * <TreeViewer
 *   data={departmentTree}
 *   selectedId={selectedDept}
 *   onSelect={(node) => setSelectedDept(node.id)}
 *   config={{ defaultExpandAll: true }}
 * />
 * ```
 */
export function TreeViewer<T extends TreeNodeData = TreeNodeData>({
  data,
  selectedId,
  onSelect,
  onDoubleClick,
  onExpandedChange,
  renderNode,
  emptyState,
  config: userConfig,
  className,
}: TreeViewerProps<T>) {
  const config = { ...DEFAULT_CONFIG, ...userConfig }

  // Initialize expanded state
  const [expandedIds, setExpandedIds] = React.useState<Set<string>>(() => {
    if (config.defaultExpandAll) {
      return new Set(collectAllIds(data))
    }
    return new Set(config.defaultExpandedIds)
  })

  // Convert selectedId to Set for consistent handling
  const selectedIds = React.useMemo(() => {
    if (!selectedId) return new Set<string>()
    if (Array.isArray(selectedId)) return new Set(selectedId)
    return new Set([selectedId])
  }, [selectedId])

  // Toggle expand/collapse
  const handleToggle = React.useCallback(
    (id: string) => {
      if (!config.collapsible) return

      setExpandedIds((prev) => {
        const next = new Set(prev)
        if (next.has(id)) {
          next.delete(id)
        } else {
          next.add(id)
        }
        onExpandedChange?.(Array.from(next))
        return next
      })
    },
    [config.collapsible, onExpandedChange]
  )

  // Handle selection
  const handleSelect = React.useCallback(
    (node: T) => {
      onSelect?.(node)
    },
    [onSelect]
  )

  // Update expanded state when defaultExpandAll changes
  React.useEffect(() => {
    if (config.defaultExpandAll) {
      setExpandedIds(new Set(collectAllIds(data)))
    }
  }, [config.defaultExpandAll, data])

  if (data.length === 0) {
    return (
      emptyState || (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          No data to display
        </div>
      )
    )
  }

  return (
    <div className={cn('select-none', className)} role="tree">
      {data.map((node) => (
        <TreeNode
          key={node.id}
          node={node as T}
          depth={0}
          expandedIds={expandedIds}
          selectedIds={selectedIds}
          config={config}
          onToggle={handleToggle}
          onSelect={handleSelect}
          onDoubleClick={onDoubleClick}
          renderNode={renderNode}
        />
      ))}
    </div>
  )
}

/**
 * Utility: Expand to a specific node
 */
export function getPathToNode<T extends TreeNodeData>(
  nodes: T[],
  targetId: string,
  path: string[] = []
): string[] | null {
  for (const node of nodes) {
    if (node.id === targetId) {
      return [...path, node.id]
    }
    if (node.children) {
      const result = getPathToNode(node.children as T[], targetId, [...path, node.id])
      if (result) return result
    }
  }
  return null
}
