import type { CortexApiClient } from './CortexApiClient'
import { MockCortexApiClient } from './mock/MockCortexApiClient'
import { HttpCortexApiClient } from './adapters/HttpCortexApiClient'

let clientInstance: CortexApiClient | null = null

export function getCortexApiClient(forceMock = false): CortexApiClient {
  if (!clientInstance) {
    const isMockEnv = forceMock || import.meta.env?.MODE === 'development' || !import.meta.env?.VITE_FRAPPE_BACKEND_URL
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
