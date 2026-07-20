import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useOfflineMockConversation } from './useOfflineMockConversation'

const ZERO_DELAYS = { reply: 0, quoteAttempt: 0, quoteRetry: 0 }

describe('useOfflineMockConversation', () => {
  it('completes the qualifying flow and resolves with a quote', async () => {
    const { result } = renderHook(() => useOfflineMockConversation({ delays: ZERO_DELAYS }))

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.status).toBe('collecting')

    act(() => result.current.sendMessage('Corolla 2018'))
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    act(() => result.current.sendMessage('35 anos, cep 01310-100'))
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    act(() => result.current.sendMessage('quero o completo'))
    await waitFor(() => expect(result.current.status).toBe('resolved'))

    const quoteMessage = result.current.messages.find((message) => message.kind === 'quote')
    expect(quoteMessage?.quote?.planoId).toBe('completo')

    const simulatedFailure = result.current.messages.find((message) => message.kind === 'error')
    expect(simulatedFailure).toBeDefined()
  })

  it('hands off to a human when the vehicle is outside the accepted age range', async () => {
    const { result } = renderHook(() => useOfflineMockConversation({ delays: ZERO_DELAYS }))

    act(() => result.current.sendMessage('é um Fusca 1990'))
    await waitFor(() => expect(result.current.status).toBe('handed_off'))

    const handoffMessage = result.current.messages.find((message) => message.kind === 'handoff')
    expect(handoffMessage).toBeDefined()
  })

  it('ignores further input once the conversation has left the collecting state', async () => {
    const { result } = renderHook(() => useOfflineMockConversation({ delays: ZERO_DELAYS }))

    act(() => result.current.sendMessage('é um Fusca 1990'))
    await waitFor(() => expect(result.current.status).toBe('handed_off'))

    const messageCountAfterHandoff = result.current.messages.length
    act(() => result.current.sendMessage('mais uma mensagem'))

    expect(result.current.messages).toHaveLength(messageCountAfterHandoff)
  })
})
