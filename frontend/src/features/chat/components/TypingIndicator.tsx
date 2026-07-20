export function TypingIndicator() {
  return (
    <div className="typing-indicator" role="status">
      <span className="typing-indicator__dot" aria-hidden="true" />
      <span className="typing-indicator__dot" aria-hidden="true" />
      <span className="typing-indicator__dot" aria-hidden="true" />
      <span className="chat-visually-hidden">O agente está digitando</span>
    </div>
  )
}
