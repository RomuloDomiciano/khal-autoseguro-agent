import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as api from './api'
import { useConversation } from './useConversation'

function agentMessage(body: string) {
  return { id: crypto.randomUUID(), role: 'agent' as const, kind: 'text' as const, body, timestamp: new Date().toISOString() }
}

describe('useConversation', () => {
  it('creates a conversation on mount and exposes the greeting', async () => {
    vi.spyOn(api, 'createConversation').mockResolvedValue({
      conversationId: 'conv_1',
      status: 'collecting',
      messages: [agentMessage('Oi!')],
    })

    const { result } = renderHook(() => useConversation())

    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].body).toBe('Oi!')
    expect(result.current.status).toBe('collecting')
  })

  it('shows a system error message if the conversation cannot be created, without throwing', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(new api.AgentServiceError('offline'))

    const { result } = renderHook(() => useConversation())

    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].kind).toBe('error')
    expect(result.current.messages[0].body).toContain('offline')
  })

  it('optimistically appends the lead message and filters it out of the server response', async () => {
    vi.spyOn(api, 'createConversation').mockResolvedValue({
      conversationId: 'conv_1',
      status: 'collecting',
      messages: [agentMessage('Oi!')],
    })
    vi.spyOn(api, 'sendMessageToAgent').mockResolvedValue({
      status: 'collecting',
      messages: [
        { id: 'echo', role: 'lead', kind: 'text', body: 'Corolla 2018', timestamp: new Date().toISOString() },
        agentMessage('E qual a sua idade?'),
      ],
    })

    const { result } = renderHook(() => useConversation())
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    act(() => result.current.sendMessage('Corolla 2018'))
    expect(result.current.messages.filter((m) => m.body === 'Corolla 2018')).toHaveLength(1)

    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))
    expect(result.current.messages.filter((m) => m.body === 'Corolla 2018')).toHaveLength(1)
    expect(result.current.messages.some((m) => m.body === 'E qual a sua idade?')).toBe(true)
  })

  it('ignores sendMessage when the conversation is not in collecting status', async () => {
    vi.spyOn(api, 'createConversation').mockResolvedValue({
      conversationId: 'conv_1',
      status: 'resolved',
      messages: [agentMessage('Tudo certo!')],
    })
    const sendSpy = vi.spyOn(api, 'sendMessageToAgent')

    const { result } = renderHook(() => useConversation())
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    act(() => result.current.sendMessage('oi de novo'))
    expect(sendSpy).not.toHaveBeenCalled()
  })

  it('startNewConversation resets to a fresh conversation after resolved/handed_off', async () => {
    const createSpy = vi.spyOn(api, 'createConversation')
    createSpy.mockResolvedValueOnce({
      conversationId: 'conv_1',
      status: 'resolved',
      messages: [agentMessage('Sua cotação: R$ 100/mês')],
    })

    const { result } = renderHook(() => useConversation())
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))
    expect(result.current.status).toBe('resolved')

    createSpy.mockResolvedValueOnce({
      conversationId: 'conv_2',
      status: 'collecting',
      messages: [agentMessage('Oi de novo!')],
    })

    act(() => result.current.startNewConversation())
    // Old messages are cleared and status resets synchronously, before the
    // new conversation's greeting arrives.
    expect(result.current.messages).toHaveLength(0)
    expect(result.current.status).toBe('collecting')
    expect(result.current.isAgentTyping).toBe(true)

    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))
    expect(result.current.messages).toEqual([expect.objectContaining({ body: 'Oi de novo!' })])
    expect(result.current.status).toBe('collecting')
    expect(createSpy).toHaveBeenCalledTimes(2)
  })

  it('startNewConversation lets sendMessage reach the new conversation id, not the old one', async () => {
    const createSpy = vi.spyOn(api, 'createConversation')
    createSpy.mockResolvedValueOnce({ conversationId: 'conv_old', status: 'resolved', messages: [] })
    const { result } = renderHook(() => useConversation())
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    createSpy.mockResolvedValueOnce({ conversationId: 'conv_new', status: 'collecting', messages: [] })
    act(() => result.current.startNewConversation())
    await waitFor(() => expect(result.current.isAgentTyping).toBe(false))

    const sendSpy = vi.spyOn(api, 'sendMessageToAgent').mockResolvedValue({ status: 'collecting', messages: [] })
    act(() => result.current.sendMessage('Corolla 2018'))
    expect(sendSpy).toHaveBeenCalledWith('conv_new', 'Corolla 2018')
  })
})
