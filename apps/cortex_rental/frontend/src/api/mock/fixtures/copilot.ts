import type { CopilotMessage } from '@/types/intelligence'

export const initialCopilotMessages: CopilotMessage[] = [
  {
    id: 'DEMO-MSG-001',
    session_id: 'DEMO-SES-001',
    sender: 'assistant',
    content: 'Bonjour Kael ! Je suis synchronisé avec la location **DEMO-TRX-2026-001** (Production Nord Inc.). Comment puis-je vous aider ?',
    state: 'idle',
    timestamp: '2026-09-02T16:00:00Z'
  }
]
