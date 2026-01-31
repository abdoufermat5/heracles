// Department types

export interface Department {
  dn: string
  ou: string
  description?: string
  path: string
  parentDn?: string
  childrenCount: number
  hrcDepartmentCategory?: string
  hrcDepartmentManager?: string
}

export interface DepartmentTreeNode {
  dn: string
  ou: string
  description?: string
  path: string
  depth: number
  children: DepartmentTreeNode[]
}

export interface DepartmentListResponse {
  departments: Department[]
  total: number
}

export interface DepartmentTreeResponse {
  tree: DepartmentTreeNode[]
  total: number
}

export interface DepartmentCreateData {
  ou: string
  description?: string
  parentDn?: string
  hrcDepartmentCategory?: string
  hrcDepartmentManager?: string
}

export interface DepartmentUpdateData {
  description?: string
  hrcDepartmentCategory?: string
  hrcDepartmentManager?: string
}

export interface DepartmentListParams {
  parent?: string
  search?: string
}
