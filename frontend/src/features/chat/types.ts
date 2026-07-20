export type MessageRole = 'lead' | 'agent' | 'system'

export type MessageKind = 'text' | 'quote' | 'handoff' | 'error'

export type PlanoId = 'essencial' | 'completo' | 'premium'

export interface QuoteSummary {
  planoId: PlanoId
  planoNome: string
  premioMensal: number
  franquia: number
  coberturas: string[]
  carenciaDias: number
  moeda: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  kind: MessageKind
  body: string
  quote?: QuoteSummary
  timestamp: string
}

export type ConversationStatus = 'collecting' | 'quoting' | 'resolved' | 'handed_off'
