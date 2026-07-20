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

  // Shared by the mount effect and startNewConversation (the "Fazer outra
  // cotação" button): fires the request and applies whatever it settles
  // with. Deliberately does nothing synchronously — react-hooks flags
  // synchronous setState calls made directly in an effect body, so the
  // mount effect below can only call this, never reset state itself;
  // startNewConversation resets state first since it runs from a click
  // handler, not an effect. isCancelled lets the mount effect opt out of
  // applying a stale response after unmount; a manual restart has no such
  // window, so it just never cancels.
  const applyNewConversation = useCallback((isCancelled: () => boolean) => {
    createConversation()
      .then((result) => {
        if (isCancelled()) return
        conversationIdRef.current = result.conversationId ?? null
        setStatus(result.status)
        setMessages(result.messages)
      })
      .catch((err: unknown) => {
        if (isCancelled()) return
        setMessages([systemErrorMessage(`Não foi possível iniciar a conversa (${reasonFor(err)}). Recarregue a página.`)])
      })
      .finally(() => {
        if (!isCancelled()) setIsAgentTyping(false)
      })
  }, [])

  useEffect(() => {
    let cancelled = false
    applyNewConversation(() => cancelled)
    return () => {
      cancelled = true
    }
  }, [applyNewConversation])

  const startNewConversation = useCallback(() => {
    conversationIdRef.current = null
    setMessages([])
    setStatus('collecting')
    setIsAgentTyping(true)
    applyNewConversation(() => false)
  }, [applyNewConversation])

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

  return { messages, status, isAgentTyping, sendMessage, startNewConversation }
}
