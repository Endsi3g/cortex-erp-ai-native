export interface HttpClientConfig {
  baseUrl?: string
  getCompanyId?: () => string | null
  getCsrfToken?: () => string | null
}

export class HttpClient {
  private baseUrl: string
  private getCompanyId: () => string | null
  private getCsrfToken: () => string | null

  constructor(config: HttpClientConfig = {}) {
    this.baseUrl = config.baseUrl || '/api/method/cortex_rental.api.v1'
    this.getCompanyId = config.getCompanyId || (() => null)
    this.getCsrfToken = config.getCsrfToken || (() => null)
  }

  public async get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin)
    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined) {
          url.searchParams.append(key, String(val))
        }
      })
    }

    const headers: Record<string, string> = {
      Accept: 'application/json'
    }

    const companyId = this.getCompanyId()
    if (companyId) {
      headers['X-Company-ID'] = companyId
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers
    })

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(errorBody.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  public async post<T>(path: string, body?: unknown, idempotencyKey?: string): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json'
    }

    const companyId = this.getCompanyId()
    if (companyId) {
      headers['X-Company-ID'] = companyId
    }

    const csrfToken = this.getCsrfToken()
    if (csrfToken) {
      headers['X-Frappe-CSRF-Token'] = csrfToken
    }

    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    })

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ message: response.statusText }))
      throw new Error(errorBody.message || `HTTP ${response.status}`)
    }

    return response.json()
  }
}
