import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ChatWindow } from './ChatWindow'
import * as api from '../api'
import type { ChatMessage } from '../types'

function agentMessage(body: string): ChatMessage {
  return { id: crypto.randomUUID(), role: 'agent', kind: 'text', body, timestamp: new Date().toISOString() }
}

describe('ChatWindow', () => {
  it('shows the greeting from agent-service and echoes a sent message while the agent replies', async () => {
    const user = userEvent.setup()
    vi.spyOn(api, 'createConversation').mockResolvedValue({
      conversationId: 'conv_1',
      status: 'collecting',
      messages: [agentMessage('Oi! Qual o modelo e o ano do veículo?')],
    })
    let resolveSend: (value: api.ConversationTurn) => void = () => {}
    vi.spyOn(api, 'sendMessageToAgent').mockReturnValue(
      new Promise((resolve) => {
        resolveSend = resolve
      }),
    )

    render(<ChatWindow />)

    expect(await screen.findByText(/qual o modelo e o ano do veículo/i)).toBeInTheDocument()

    const input = screen.getByLabelText('Mensagem')
    await user.type(input, 'Corolla 2018')
    await user.click(screen.getByRole('button', { name: /enviar/i }))

    expect(screen.getByText('Corolla 2018')).toBeInTheDocument()
    expect(input).toHaveValue('')
    expect(input).toBeDisabled()
    expect(screen.getByRole('status')).toBeInTheDocument()

    resolveSend({ status: 'collecting', messages: [agentMessage('E qual a sua idade?')] })
    expect(await screen.findByText(/qual a sua idade/i)).toBeInTheDocument()
  })

  it('does not allow sending an empty message', async () => {
    vi.spyOn(api, 'createConversation').mockResolvedValue({
      conversationId: 'conv_2',
      status: 'collecting',
      messages: [agentMessage('Oi!')],
    })
    render(<ChatWindow />)
    await screen.findByText('Oi!')
    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled()
  })

  it('shows a safe error message and does not crash when agent-service is unreachable', async () => {
    vi.spyOn(api, 'createConversation').mockRejectedValue(new api.AgentServiceError('Não foi possível conectar ao agente.'))
    render(<ChatWindow />)
    expect(await screen.findByText(/não foi possível iniciar a conversa/i)).toBeInTheDocument()
  })
})
