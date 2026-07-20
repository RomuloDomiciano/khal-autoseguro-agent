import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import { MessageInput } from './MessageInput'
import { TypingIndicator } from './TypingIndicator'
import { useConversation } from '../useConversation'

const STATUS_LABEL: Record<string, string> = {
  collecting: 'Em atendimento',
  quoting: 'Calculando cotação...',
  resolved: 'Cotação concluída',
  handed_off: 'Transferido para um consultor',
}

const TERMINAL_STATUSES = new Set(['resolved', 'handed_off'])

export function ChatWindow() {
  const { messages, status, isAgentTyping, sendMessage, startNewConversation } = useConversation()
  const listRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    const list = listRef.current
    if (typeof list?.scrollTo === 'function') {
      list.scrollTo({ top: list.scrollHeight })
    }
  }, [messages, isAgentTyping])

  const isTerminal = TERMINAL_STATUSES.has(status)
  const inputDisabled = isAgentTyping || status !== 'collecting'
  const disabledReason = status !== 'collecting' ? STATUS_LABEL[status] : undefined

  return (
    <section className="chat-window" aria-label="Conversa com o agente AutoSeguro">
      <header className="chat-window__header">
        <h1>AutoSeguro</h1>
        <span className={`chat-window__status chat-window__status--${status}`}>{STATUS_LABEL[status]}</span>
      </header>

      <ul className="chat-window__messages" role="log" aria-live="polite" ref={listRef}>
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isAgentTyping && (
          <li className="chat-message chat-message--agent">
            <div className="chat-message__bubble">
              <TypingIndicator />
            </div>
          </li>
        )}
      </ul>

      {isTerminal ? (
        <div className="chat-window__restart">
          <button type="button" className="chat-window__restart-button" onClick={startNewConversation}>
            Fazer outra cotação
          </button>
        </div>
      ) : (
        <MessageInput disabled={inputDisabled} disabledReason={disabledReason} onSend={sendMessage} />
      )}
    </section>
  )
}
