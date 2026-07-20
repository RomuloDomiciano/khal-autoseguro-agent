import { QuoteCard } from './QuoteCard'
import type { ChatMessage } from '../types'

const timeFormatter = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })

interface MessageBubbleProps {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.kind === 'error') {
    return (
      <li className="chat-message chat-message--system" aria-live="polite">
        <p className="chat-message__notice chat-message__notice--error">{message.body}</p>
      </li>
    )
  }

  const alignment = message.role === 'lead' ? 'chat-message--lead' : 'chat-message--agent'

  return (
    <li className={`chat-message ${alignment}`}>
      <div
        className={`chat-message__bubble${message.kind === 'handoff' ? ' chat-message__bubble--handoff' : ''}`}
      >
        <p>{message.body}</p>
        {message.kind === 'quote' && message.quote && <QuoteCard quote={message.quote} />}
      </div>
      <time className="chat-message__time" dateTime={message.timestamp}>
        {timeFormatter.format(new Date(message.timestamp))}
      </time>
    </li>
  )
}
