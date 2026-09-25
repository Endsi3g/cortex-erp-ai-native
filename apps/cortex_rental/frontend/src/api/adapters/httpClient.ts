export interface HttpClientConfig {
  baseUrl?: string
  getCompanyId?: () => string | null
  getCsrfToken?: () => string | null
}

/** Error raised for any non-2xx Frappe response, with the server's own message. */
export class CortexApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly excType: string | null = null
  ) {
    super(message)
    this.name = 'CortexApiError'
  }

  get isPermissionError(): boolean {
    return this.status === 403 || this.excType === 'PermissionError'
  }

  get isValidationError(): boolean {
    return this.status === 417 || this.excType === 'ValidationError'
  }
}

type Params = Record<string, string | number | boolean | undefined | null>

function defaultCsrfToken(): string | null {
  if (typeof window === 'undefined') return null
  // Injected by www/cortex.html (frappe-ui jinjaBootData), or by Desk.
  const bootToken = (window as Window & { csrf_token?: string }).csrf_token
  if (bootToken && bootToken !== '{{ csrf_token }}') return bootToken
  const deskToken = (window as Window & { frappe?: { csrf_token?: string } }).frappe?.csrf_token
  if (deskToken) return deskToken
  if (typeof document === 'undefined') return null
  const cookie = document.cookie.split('; ').find(entry => entry.startsWith('csrf_token='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : null
}

/** Frappe error bodies carry `_server_messages` (a JSON list of JSON strings), `exception` and `exc_type`. */
async function toApiError(response: Response): Promise<CortexApiError> {
  const body = await response.json().catch(() => null) as Record<string, unknown> | null
  let message: string | null = null
  if (body && typeof body._server_messages === 'string') {
    try {
      const messages = (JSON.parse(body._server_messages) as string[]).map(entry => {
        try { return (JSON.parse(entry) as { message?: string }).message ?? entry } catch { return entry }
      })
      message = messages.join(' ').replace(/<[^>]+>/g, '').trim() || null
    } catch {
      message = null
    }
  }
  if (!message && body && typeof body.exception === 'string') {
    message = body.exception.split(':').slice(1).join(':').trim() || body.exception
  }
  if (!message && body && typeof body.message === 'string') message = body.message
  return new CortexApiError(
    message || `Le serveur a répondu ${response.status}.`,
    response.status,
    body && typeof body.exc_type === 'string' ? body.exc_type : null
  )
}

export class HttpClient {
  private baseUrl: string
  private getCompanyId: () => string | null
  private getCsrfToken: () => string | null

  constructor(config: HttpClientConfig = {}) {
    this.baseUrl = config.baseUrl || '/api/method'
    this.getCompanyId = config.getCompanyId || (() => typeof localStorage !== 'undefined' ? localStorage.getItem('cortex_active_company_id') : null)
    this.getCsrfToken = config.getCsrfToken || defaultCsrfToken
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { Accept: 'application/json', ...extra }
    const companyId = this.getCompanyId()
    if (companyId) headers['X-Company-ID'] = companyId
    return headers
  }

  public async get<T>(path: string, params?: Params): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin)
    Object.entries(params ?? {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') url.searchParams.append(key, String(value))
    })
    const response = await fetch(url.toString(), { method: 'GET', headers: this.headers(), credentials: 'include' })
    if (!response.ok) throw await toApiError(response)
    return response.json()
  }

  public async post<T>(path: string, body?: unknown, idempotencyKey?: string): Promise<T> {
    const extra: Record<string, string> = { 'Content-Type': 'application/json' }
    const csrfToken = this.getCsrfToken()
    if (csrfToken) extra['X-Frappe-CSRF-Token'] = csrfToken
    if (idempotencyKey) extra['Idempotency-Key'] = idempotencyKey
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.headers(extra),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined
    })
    if (!response.ok) throw await toApiError(response)
    return response.json()
  }

  /** multipart upload to Frappe's upload_file (private file attached to a document). */
  public async upload<T>(path: string, form: FormData): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' }
    const csrfToken = this.getCsrfToken()
    if (csrfToken) headers['X-Frappe-CSRF-Token'] = csrfToken
    const companyId = this.getCompanyId()
    if (companyId) headers['X-Company-ID'] = companyId
    const response = await fetch(`${this.baseUrl}${path}`, { method: 'POST', headers, credentials: 'include', body: form })
    if (!response.ok) throw await toApiError(response)
    return response.json()
  }
}
