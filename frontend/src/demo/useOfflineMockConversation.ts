import { useCallback, useRef, useState } from 'react'
import {
  advanceConversation,
  buildQuote,
  createMessage,
  greetingMessage,
  initialCollectedData,
  type CollectedData,
  type CompletedData,
  type PendingField,
} from './offlineMockAgent'
import type { ChatMessage, ConversationStatus } from '../features/chat/types'

/**
 * OFFLINE DEMO ONLY — NOT PRODUCTION.
 *
 * Drives offlineMockAgent.ts's scripted state machine for UI demo purposes
 * with no backend running. The real app uses
 * `features/chat/useConversation.ts`, which talks to the real
 * agent-service. Do not wire this hook into production UI.
 */
const DEFAULT_REPLY_DELAY_MS = 700
const DEFAULT_QUOTE_ATTEMPT_DELAY_MS = 900
const DEFAULT_QUOTE_RETRY_DELAY_MS = 1100

export interface UseOfflineMockConversationOptions {
  /** Overridable delays, mainly for deterministic tests. */
  delays?: {
    reply?: number
    quoteAttempt?: number
    quoteRetry?: number
  }
}

interface InternalState {
  pendingField: PendingField
  data: CollectedData
  attempts: number
}

export function useOfflineMockConversation(options: UseOfflineMockConversationOptions = {}) {
  const replyDelay = options.delays?.reply ?? DEFAULT_REPLY_DELAY_MS
  const quoteAttemptDelay = options.delays?.quoteAttempt ?? DEFAULT_QUOTE_ATTEMPT_DELAY_MS
  const quoteRetryDelay = options.delays?.quoteRetry ?? DEFAULT_QUOTE_RETRY_DELAY_MS

  const [messages, setMessages] = useState<ChatMessage[]>(() => [greetingMessage()])
  const [status, setStatus] = useState<ConversationStatus>('collecting')
  const [isAgentTyping, setIsAgentTyping] = useState(false)

  const internal = useRef<InternalState>({
    pendingField: 'veiculoAno',
    data: initialCollectedData(),
    attempts: 0,
  })

  const runQuoteSequence = useCallback(
    (data: CompletedData) => {
      setStatus('quoting')
      setIsAgentTyping(true)

      window.setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          createMessage(
            'system',
            'error',
            'Serviço de cotação temporariamente indisponível. Tentando novamente...',
          ),
        ])

        window.setTimeout(() => {
          setIsAgentTyping(false)
          const quote = buildQuote(data.planoId, data.idade, data.veiculoAno, data.cep)
          setMessages((prev) => [
            ...prev,
            createMessage('agent', 'quote', `Consegui sua cotação no plano ${quote.planoNome}!`, quote),
          ])
          setStatus('resolved')
        }, quoteRetryDelay)
      }, quoteAttemptDelay)
    },
    [quoteAttemptDelay, quoteRetryDelay],
  )

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || status !== 'collecting') return

      setMessages((prev) => [...prev, createMessage('lead', 'text', trimmed)])
      setIsAgentTyping(true)

      window.setTimeout(() => {
        const result = advanceConversation({
          pendingField: internal.current.pendingField,
          data: internal.current.data,
          attempts: internal.current.attempts,
          leadText: trimmed,
        })

        internal.current = {
          pendingField: result.pendingField,
          data: result.data,
          attempts: result.attempts,
        }

        if (result.outcome === 'ready_to_quote') {
          setMessages((prev) => [...prev, ...result.agentMessages])
          runQuoteSequence(result.data)
          return
        }

        setIsAgentTyping(false)
        setMessages((prev) => [...prev, ...result.agentMessages])
        if (result.outcome === 'handoff') {
          setStatus('handed_off')
        }
      }, replyDelay)
    },
    [status, replyDelay, runQuoteSequence],
  )

  return { messages, status, isAgentTyping, sendMessage }
}
