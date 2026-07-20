import type { ChatMessage, ConversationStatus, MessageKind, MessageRole, PlanoId } from './types'

const BASE_URL = `${import.meta.env.VITE_AGENT_SERVICE_URL ?? 'http://localhost:8080'}/api/v1`

// A single POST /messages call can legitimately take a while: the backend
// may need one LLM call *and* a full quote-service retry cycle before it
// can answer (either with a quote or a handoff), and this timeout must
// never fire while the backend is still doing that legitimate work — see
// agent-service/README.md's "read timeout" and retry-policy sections.
//
// Budget, from agent-service/app/config/settings.py's defaults:
//   quote-service retries:  quote_service_max_attempts (3) *
//                            quote_service_read_timeout_seconds (15s)
//                            + exponential backoff/jitter between attempts   ~= 47s
//   LLM call:                llm_timeout_seconds (20s) *
//                            (1 + llm_max_retries (1)), plus the OpenAI
//                            SDK's own backoff between retries              ~= 45s
//   -------------------------------------------------------------------------
//   backend worst-case synchronous duration                                ~= 92s
//
// 100s keeps a small margin above that for network transit and JSON
// (de)serialization, without adding unbounded slack. If either backend
// budget changes, this constant must be re-derived from it.
const REQUEST_TIMEOUT_MS = 100_000

interface ApiQuoteSummary {
  planoId: PlanoId
  planoNome: string
  premioMensal: number
  franquia: number
  coberturas: string[]
  carenciaDias: number
  moeda: string
}

interface ApiMessage {
  id: string
  role: MessageRole
  kind: MessageKind
  body: string
  quoteSummary: ApiQuoteSummary | null
  createdAt: string
}

interface TurnResponse {
  conversationId: string
  status: ConversationStatus
  messages: ApiMessage[]
}

export class AgentServiceError extends Error {}

function toChatMessage(message: ApiMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    kind: message.kind,
    body: message.body,
    quote: message.quoteSummary ?? undefined,
    timestamp: message.createdAt,
  }
}

async function request(path: string, init?: RequestInit): Promise<TurnResponse> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      signal: controller.signal,
    })
  } catch {
    throw new AgentServiceError('Não foi possível conectar ao agente.')
  } finally {
    window.clearTimeout(timeoutId)
  }

  if (!response.ok) {
    throw new AgentServiceError(`O agente respondeu com um erro (${response.status}).`)
  }
  return (await response.json()) as TurnResponse
}

export interface ConversationTurn {
  conversationId?: string
  status: ConversationStatus
  messages: ChatMessage[]
}

export async function createConversation(): Promise<ConversationTurn> {
  const res = await request('/conversations', { method: 'POST' })
  return { conversationId: res.conversationId, status: res.status, messages: res.messages.map(toChatMessage) }
}

export async function sendMessageToAgent(conversationId: string, body: string): Promise<ConversationTurn> {
  const res = await request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  })
  return { status: res.status, messages: res.messages.map(toChatMessage) }
}
