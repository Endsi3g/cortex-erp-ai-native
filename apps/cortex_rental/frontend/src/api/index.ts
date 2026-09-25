import type { CortexApiClient } from './CortexApiClient'
import { MockCortexApiClient } from './mock/MockCortexApiClient'
import { HttpCortexApiClient } from './adapters/HttpCortexApiClient'

let clientInstance: CortexApiClient | null = null

export function shouldUseMockApi(input: {
  forceMock?: boolean
  mode?: string
  backendUrl?: string
  frappeAvailable?: boolean
}): boolean {
  if (input.forceMock) return true
  if (input.frappeAvailable) return false
  if (input.backendUrl) return false
  return false
}

export function getCortexApiClient(forceMock = false): CortexApiClient {
  if (!clientInstance) {
    const frappe = typeof window !== 'undefined'
      ? (window as Window & { frappe?: { call?: unknown } }).frappe
      : undefined
    const runningInsideFrappe = typeof frappe?.call === 'function'
    const isMockEnv = shouldUseMockApi({
      mode: import.meta.env?.MODE,
      backendUrl: import.meta.env?.VITE_FRAPPE_BACKEND_URL,
      forceMock: forceMock || import.meta.env?.VITE_USE_MOCK_API === 'true',
      frappeAvailable: runningInsideFrappe
    })
    clientInstance = isMockEnv ? new MockCortexApiClient() : new HttpCortexApiClient()
  }
  return clientInstance
}

export function setCortexApiClient(client: CortexApiClient): void {
  clientInstance = client
}

export * from './CortexApiClient'
export * from './contracts'
export * from './adapters'
export * from './mock'
