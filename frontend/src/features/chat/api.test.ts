import { afterEach, describe, expect, it, vi } from 'vitest'
import { AgentServiceError, createConversation, sendMessageToAgent } from './api'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('createConversation', () => {
  it('maps the API response into ConversationTurn / ChatMessage shapes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          conversationId: 'conv_1',
          status: 'collecting',
          messages: [
            {
              id: 'msg_1',
              role: 'agent',
              kind: 'text',
              body: 'Oi!',
              quoteSummary: null,
              createdAt: '2026-07-19T00:00:00Z',
            },
          ],
        }),
      ),
    )

    const result = await createConversation()

    expect(result.conversationId).toBe('conv_1')
    expect(result.status).toBe('collecting')
    expect(result.messages).toEqual([
      { id: 'msg_1', role: 'agent', kind: 'text', body: 'Oi!', quote: undefined, timestamp: '2026-07-19T00:00:00Z' },
    ])
  })

  it('maps a quote message, converting quoteSummary to quote', async () => {
    const quoteSummary = {
      planoId: 'completo',
      planoNome: 'Completo',
      premioMensal: 241.38,
      franquia: 3000,
      coberturas: ['colisao'],
      carenciaDias: 30,
      moeda: 'BRL',
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          conversationId: 'conv_1',
          status: 'resolved',
          messages: [
            {
              id: 'msg_2',
              role: 'agent',
              kind: 'quote',
              body: 'Consegui sua cotação!',
              quoteSummary,
              createdAt: '2026-07-19T00:00:01Z',
            },
          ],
        }),
      ),
    )

    const result = await sendMessageToAgent('conv_1', 'quero o completo')
    expect(result.messages[0].quote).toEqual(quoteSummary)
  })

  it('throws AgentServiceError on a non-2xx response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(createConversation()).rejects.toThrow(AgentServiceError)
  })

  it('throws AgentServiceError when the network request itself fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    )
    await expect(createConversation()).rejects.toThrow(AgentServiceError)
  })

  it('does not abort while the backend is still within its documented retry/LLM budget', async () => {
    vi.useFakeTimers()
    try {
      let capturedSignal: AbortSignal | undefined
      vi.stubGlobal(
        'fetch',
        vi.fn((_url: string, init?: RequestInit) => {
          capturedSignal = init?.signal ?? undefined
          return new Promise<Response>(() => {}) // simulates a slow backend that never returns
        }),
      )

      const pending = createConversation()
      pending.catch(() => {})

      // Just under the documented ~92s backend worst case (3 quote-service
      // attempts * 15s + backoff, plus one LLM call with its retry) — must
      // not have been aborted yet.
      await vi.advanceTimersByTimeAsync(90_000)
      expect(capturedSignal?.aborted).toBe(false)
    } finally {
      vi.useRealTimers()
    }
  })

  it('aborts once the request timeout is exceeded', async () => {
    vi.useFakeTimers()
    try {
      let capturedSignal: AbortSignal | undefined
      vi.stubGlobal(
        'fetch',
        vi.fn((_url: string, init?: RequestInit) => {
          capturedSignal = init?.signal ?? undefined
          return new Promise<Response>(() => {})
        }),
      )

      const pending = createConversation()
      pending.catch(() => {})

      await vi.advanceTimersByTimeAsync(100_000)
      expect(capturedSignal?.aborted).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })
})
