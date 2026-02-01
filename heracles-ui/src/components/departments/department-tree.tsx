'use client'

import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Users, FolderCog } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { TreeViewer, type TreeNodeData, type TreeNodeRenderProps } from '@/components/common'
import { useDepartmentStore } from '@/stores'
import { ROUTES } from '@/config/routes'
import type { DepartmentTreeNode } from '@/types'

/**
 * Extended tree node with department-specific data
 */
interface DepartmentNode extends TreeNodeData {
  path: string
  depth: number
  description?: string
}

/**
 * Convert API department tree to TreeViewer format
 */
function convertToTreeNodes(nodes: DepartmentTreeNode[]): DepartmentNode[] {
  return nodes.map((node) => ({
    id: node.dn,
    label: node.ou,
    path: node.path,
    depth: node.depth,
    description: node.description,
    children: node.children?.length ? convertToTreeNodes(node.children) : undefined,
    data: {
      dn: node.dn,
      ou: node.ou,
    },
  }))
}

/**
 * Custom department node renderer
 */
function DepartmentNodeRenderer({
  node,
  depth,
  isExpanded,
  isSelected,
  hasChildren,
  onToggle,
  onSelect,
}: TreeNodeRenderProps<DepartmentNode>) {
  const navigate = useNavigate()

  return (
    <div
      className={cn(
        'group flex items-center gap-2 py-1.5 px-2 rounded-md cursor-pointer transition-colors',
        'hover:bg-accent/50',
        isSelected && 'bg-primary/10 text-primary'
      )}
      onClick={onSelect}
    >
      {/* Expand/Collapse */}
      {hasChildren ? (
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 p-0 opacity-70 hover:opacity-100"
          onClick={(e) => {
            e.stopPropagation()
            onToggle()
          }}
        >
          <svg
            className={cn(
              'h-4 w-4 transition-transform',
              isExpanded && 'rotate-90'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Button>
      ) : (
        <span className="w-5" />
      )}

      {/* Icon */}
      <Building2
        className={cn(
          'h-4 w-4 shrink-0',
          isSelected ? 'text-primary' : 'text-amber-500'
        )}
      />

      {/* Label and path */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{node.label}</span>
          {hasChildren && (
            <Badge variant="secondary" className="text-xs h-5">
              {node.children?.length}
            </Badge>
          )}
        </div>
        {depth === 0 && node.description && (
          <div className="text-xs text-muted-foreground truncate">
            {node.description}
          </div>
        )}
      </div>

      {/* Actions (visible on hover) */}
      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={(e) => {
            e.stopPropagation()
            navigate(ROUTES.DEPARTMENT_DETAIL.replace(':dn', encodeURIComponent(node.id)))
          }}
          title="View details"
        >
          <FolderCog className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={(e) => {
            e.stopPropagation()
            // Filter users by this department
            navigate(`${ROUTES.USERS}?department=${encodeURIComponent(node.id)}`)
          }}
          title="View users"
        >
          <Users className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

interface DepartmentTreeProps {
  /** Department tree data from API */
  data: DepartmentTreeNode[]
  /** Called when a department is selected */
  onSelect?: (node: DepartmentNode) => void
  /** Currently selected department DN */
  selectedDn?: string
  /** Whether to expand all nodes by default */
  defaultExpandAll?: boolean
  /** Additional class name */
  className?: string
}

/**
 * Department tree viewer component.
 * Displays organizational hierarchy with expand/collapse and navigation.
 * 
 * @example
 * ```tsx
 * <DepartmentTree
 *   data={departmentTree}
 *   selectedDn={currentDepartment}
 *   onSelect={(node) => setCurrentDepartment(node.id)}
 * />
 * ```
 */
export function DepartmentTree({
  data,
  onSelect,
  selectedDn,
  defaultExpandAll = true,
  className,
}: DepartmentTreeProps) {
  const { setCurrentBase } = useDepartmentStore()

  const treeData = React.useMemo(() => convertToTreeNodes(data), [data])

  const handleSelect = React.useCallback(
    (node: DepartmentNode) => {
      setCurrentBase(node.id, node.path)
      onSelect?.(node)
    },
    [setCurrentBase, onSelect]
  )

  return (
    <TreeViewer
      data={treeData}
      selectedId={selectedDn}
      onSelect={handleSelect}
      renderNode={DepartmentNodeRenderer}
      config={{
        defaultExpandAll,
        showLines: false,
        indentSize: 16,
        animationDuration: 150,
      }}
      className={className}
      emptyState={
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
          <Building2 className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">No departments found</p>
        </div>
      }
    />
  )
}
