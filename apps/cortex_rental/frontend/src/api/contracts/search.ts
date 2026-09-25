export type GlobalSearchResultType = 'rental' | 'customer' | 'equipment' | 'serial'

export interface GlobalSearchResult {
  type: GlobalSearchResultType
  id: string
  title: string
  subtitle: string
}

export interface GlobalSearchResponse {
  query: string
  results: GlobalSearchResult[]
}
