import type { AgentRunTelemetry } from '@/types/intelligence'

export const initialTelemetryRuns: AgentRunTelemetry[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    run_id: 'DEMO-TEL-001',
    agent_name: 'Cortex Intake',
    started_at: '2026-09-02T08:34:50Z',
    ended_at: '2026-09-02T08:35:00Z',
    duration_ms: 10240,
    model_used: 'gemini-2.5-pro',
    prompt_tokens: 3420,
    completion_tokens: 480,
    total_cost_cad: 0.042,
    tools_invoked: [
      { tool_name: 'parse_email_entities', latency_ms: 820, status: 'success' },
      { tool_name: 'match_catalog_items', latency_ms: 350, status: 'success' },
      { tool_name: 'check_preliminary_availability', latency_ms: 410, status: 'success' }
    ],
    status: 'completed'
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    run_id: 'DEMO-TEL-002',
    agent_name: 'Cortex Availability',
    started_at: '2026-09-02T09:12:00Z',
    ended_at: '2026-09-02T09:12:04Z',
    duration_ms: 4100,
    model_used: 'gemini-2.5-flash',
    prompt_tokens: 1850,
    completion_tokens: 220,
    total_cost_cad: 0.008,
    tools_invoked: [
      { tool_name: 'query_fleet_temporal_locks', latency_ms: 180, status: 'success' }
    ],
    status: 'completed'
  }
]
