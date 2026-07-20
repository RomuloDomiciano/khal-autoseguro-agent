import { useCallback, useEffect, useRef, useState } from 'react'
import { AgentServiceError, createConversation, sendMessageToAgent } from './api'
import type { ChatMessage, ConversationStatus } from './types'

function systemErrorMessage(body: string): ChatMessage {
  return { id: crypto.randomUUID(), role: 'system', kind: 'error', body, timestamp: new Date().toISOString() }
}

function leadMessage(body: string): ChatMessage {
  return { id: crypto.randomUUID(), role: 'lead', kind: 'text', body, timestamp: new Date().toISOString() }
}

function reasonFor(err: unknown): string {
  return err instanceof AgentServiceError ? err.message : 'erro desconhecido'
}

/** Talks to the real agent-service. Exposes the same shape as the original
 * offline demo hook (now `../../demo/useOfflineMockConversation.ts`) so
 * ChatWindow didn't need to change beyond the import — this is the seam
 * the demo was always meant to be swapped at for production use. */
export function useConversation() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ConversationStatus>('collecting')
  const [isAgentTyping, setIsAgentTyping] = useState(true)
  const conversationIdRef = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false

    createConversation()
      .then((result) => {
        if (cancelled) return
        conversationIdRef.current = result.conversationId ?? null
        setStatus(result.status)
        setMessages(result.messages)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setMessages([systemErrorMessage(`Não foi possível iniciar a conversa (${reasonFor(err)}). Recarregue a página.`)])
      })
      .finally(() => {
        if (!cancelled) setIsAgentTyping(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      const conversationId = conversationIdRef.current
      if (!trimmed || status !== 'collecting' || !conversationId) return

      setMessages((prev) => [...prev, leadMessage(trimmed)])
      setIsAgentTyping(true)

      sendMessageToAgent(conversationId, trimmed)
        .then((result) => {
          setStatus(result.status)
          // The API returns every message produced this turn, including the
          // lead's own message we already appended optimistically above.
          setMessages((prev) => [...prev, ...result.messages.filter((message) => message.role !== 'lead')])
        })
        .catch((err: unknown) => {
          setMessages((prev) => [
            ...prev,
            systemErrorMessage(`Tivemos um problema para falar com o agente (${reasonFor(err)}). Tente novamente.`),
          ])
        })
        .finally(() => setIsAgentTyping(false))
    },
    [status],
  )

  return { messages, status, isAgentTyping, sendMessage }
}
