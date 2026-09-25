export type DataProvenance = 'demo' | 'mock' | 'api' | 'realtime' | 'stale'

export interface ProvenanceMeta {
  provenance: DataProvenance
  last_synced_at: string
  etag?: string
  version?: number
}

export interface TenantCompany {
  id: string
  name: string
  code: string
  currency: 'CAD'
  timezone: string
  is_active: boolean
}

export interface UserProfile {
  id: string
  email: string
  full_name: string
  role: 'Operations Lead' | 'Rental Agent' | 'Warehouse Tech' | 'Finance Lead' | 'System Admin'
  roles: string[]
  permissions: string[]
  language: 'fr-CA' | 'en-CA'
  authorized_companies: string[]
  active_company_id: string
}

export interface PaginationParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PaginatedResult<T> {
  items: T[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}
