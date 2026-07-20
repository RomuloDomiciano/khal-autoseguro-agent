import type { ChatMessage, MessageKind, MessageRole, PlanoId, QuoteSummary } from '../features/chat/types'

/**
 * OFFLINE DEMO ONLY — NOT PRODUCTION, NOT THE SOURCE OF TRUTH FOR PRICE.
 *
 * The real app (`features/chat/useConversation.ts` + `api.ts`) talks to the
 * real agent-service, which is the only authoritative source of quotes and
 * business rules. This file is a fully client-side, backend-free stand-in
 * kept solely so the UI can be demoed/screenshotted without running
 * quote-service or agent-service. It duplicates quote-service's
 * data/plans.json pricing rules as of the time it was written and WILL
 * drift — never use it, or its output, to inform a real quote.
 */
const IDADE_MIN = 18
const IDADE_MAX = 75
const VEICULO_MAX_ANOS = 20
const MAX_ATTEMPTS_PER_FIELD = 2

const PLANOS: Record<PlanoId, { nome: string; premioBase: number; franquia: number; coberturas: string[] }> = {
  essencial: { nome: 'Essencial', premioBase: 119.9, franquia: 4500, coberturas: ['colisão', 'roubo', 'furto'] },
  completo: {
    nome: 'Completo',
    premioBase: 209.9,
    franquia: 3000,
    coberturas: ['colisão', 'roubo', 'furto', 'terceiros', 'vidros'],
  },
  premium: {
    nome: 'Premium',
    premioBase: 339.9,
    franquia: 1500,
    coberturas: ['colisão', 'roubo', 'furto', 'terceiros', 'vidros', 'carro reserva', 'assistência 24h'],
  },
}

const CEP_PREFIXOS_ALTO_RISCO = ['07', '08', '21', '26', '59']

function faixaEtariaMultiplicador(idade: number): number {
  if (idade <= 24) return 1.6
  if (idade <= 29) return 1.25
  if (idade <= 59) return 1.0
  return 1.4
}

function idadeVeiculoMultiplicador(anosVeiculo: number): number {
  if (anosVeiculo <= 5) return 1.0
  if (anosVeiculo <= 10) return 1.15
  return 1.45
}

function regiaoMultiplicador(cep: string | null): number {
  if (!cep) return 1.0
  const prefixo = cep.replace(/\D/g, '').slice(0, 2)
  return CEP_PREFIXOS_ALTO_RISCO.includes(prefixo) ? 1.3 : 1.0
}

export function isIdadeAceita(idade: number): boolean {
  return idade >= IDADE_MIN && idade <= IDADE_MAX
}

export function isVeiculoAceito(veiculoAno: number, anoAtual = new Date().getFullYear()): boolean {
  const anos = anoAtual - veiculoAno
  return anos >= 0 && anos <= VEICULO_MAX_ANOS
}

export function buildQuote(
  planoId: PlanoId,
  idade: number,
  veiculoAno: number,
  cep: string | null,
  anoAtual = new Date().getFullYear(),
): QuoteSummary {
  const plano = PLANOS[planoId]
  const anosVeiculo = anoAtual - veiculoAno
  const multiplicador =
    faixaEtariaMultiplicador(idade) * idadeVeiculoMultiplicador(anosVeiculo) * regiaoMultiplicador(cep)
  const premioMensal = Math.round(plano.premioBase * multiplicador * 100) / 100

  return {
    planoId,
    planoNome: plano.nome,
    premioMensal,
    franquia: plano.franquia,
    coberturas: plano.coberturas,
    carenciaDias: 30,
    moeda: 'BRL',
  }
}

export function extractIdade(text: string): number | null {
  const match = text.match(/(\d{1,3})\s*anos?\b/i) ?? text.match(/idade[^\d]{0,10}(\d{1,3})/i)
  if (!match) return null
  const idade = Number(match[1])
  return idade > 0 && idade < 130 ? idade : null
}

export function extractVeiculoAno(text: string, anoAtual = new Date().getFullYear()): number | null {
  const matches = [...text.matchAll(/(19[5-9]\d|20\d{2})/g)]
  if (matches.length === 0) return null
  const ano = Number(matches[matches.length - 1][1])
  return ano >= 1950 && ano <= anoAtual + 1 ? ano : null
}

export function extractCep(text: string): string | null {
  const match = text.match(/\d{5}-?\d{3}/)
  return match ? match[0] : null
}

export function extractPlano(text: string): PlanoId | null {
  const lower = text.toLowerCase()
  if (lower.includes('premium')) return 'premium'
  if (lower.includes('completo')) return 'completo'
  if (lower.includes('essencial') || lower.includes('básico') || lower.includes('basico')) return 'essencial'
  return null
}

export function createMessage(role: MessageRole, kind: MessageKind, body: string, quote?: QuoteSummary): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    kind,
    body,
    quote,
    timestamp: new Date().toISOString(),
  }
}

export function greetingMessage(): ChatMessage {
  return createMessage(
    'agent',
    'text',
    'Oi! Aqui é da AutoSeguro 👋 Vou te ajudar a cotar o seguro do seu carro. Pra começar, me conta: qual o modelo e o ano do veículo?',
  )
}

export type PendingField = 'veiculoAno' | 'idade' | 'cep' | 'plano' | 'done'

export interface CollectedData {
  veiculoAno: number | null
  idade: number | null
  cep: string | null
  planoId: PlanoId | null
}

export interface CompletedData {
  veiculoAno: number
  idade: number
  cep: string | null
  planoId: PlanoId
}

export function initialCollectedData(): CollectedData {
  return { veiculoAno: null, idade: null, cep: null, planoId: null }
}

interface AdvanceInput {
  pendingField: PendingField
  data: CollectedData
  attempts: number
  leadText: string
}

type AdvanceResult =
  | { outcome: 'ask'; agentMessages: ChatMessage[]; pendingField: PendingField; data: CollectedData; attempts: number }
  | { outcome: 'handoff'; agentMessages: ChatMessage[]; pendingField: 'done'; data: CollectedData; attempts: number }
  | { outcome: 'ready_to_quote'; agentMessages: ChatMessage[]; pendingField: 'done'; data: CompletedData; attempts: number }

function handoff(data: CollectedData, attempts: number, reason: string): AdvanceResult {
  return {
    outcome: 'handoff',
    agentMessages: [createMessage('agent', 'handoff', reason)],
    pendingField: 'done',
    data,
    attempts,
  }
}

function askAgain(data: CollectedData, pendingField: PendingField, attempts: number, prompt: string): AdvanceResult {
  return {
    outcome: 'ask',
    agentMessages: [createMessage('agent', 'text', prompt)],
    pendingField,
    data,
    attempts,
  }
}

export function advanceConversation({ pendingField, data, attempts, leadText }: AdvanceInput): AdvanceResult {
  switch (pendingField) {
    case 'veiculoAno': {
      const ano = extractVeiculoAno(leadText)
      if (ano === null) {
        if (attempts + 1 >= MAX_ATTEMPTS_PER_FIELD) {
          return handoff(
            data,
            attempts + 1,
            'Não consegui identificar o modelo/ano do veículo pelo que você escreveu. Vou te transferir para um consultor te ajudar por aqui.',
          )
        }
        return askAgain(
          data,
          'veiculoAno',
          attempts + 1,
          'Não entendi o ano do veículo. Pode confirmar, por exemplo "Corolla 2018"?',
        )
      }
      if (!isVeiculoAceito(ano)) {
        return handoff(
          data,
          0,
          `Esse veículo tem mais de ${VEICULO_MAX_ANOS} anos e está fora da nossa política de aceitação no momento. Vou te transferir para um consultor, que pode avaliar outras opções com você.`,
        )
      }
      return askAgain(
        { ...data, veiculoAno: ano },
        'idade',
        0,
        'Perfeito! Agora preciso da sua idade e do CEP onde o carro fica. Pode mandar os dois numa mensagem, tipo "35 anos, CEP 01310-100"?',
      )
    }

    case 'idade': {
      const idade = extractIdade(leadText)
      const cep = extractCep(leadText) ?? data.cep
      if (idade === null) {
        if (attempts + 1 >= MAX_ATTEMPTS_PER_FIELD) {
          return handoff(
            data,
            attempts + 1,
            'Não consegui identificar sua idade pelo que você escreveu. Vou te transferir para um consultor te ajudar por aqui.',
          )
        }
        return askAgain(data, 'idade', attempts + 1, 'Não entendi sua idade. Pode me dizer, tipo "tenho 35 anos"?')
      }
      if (!isIdadeAceita(idade)) {
        return handoff(
          { ...data, idade },
          0,
          `Pela nossa política, não fechamos seguro para condutores fora da faixa de ${IDADE_MIN} a ${IDADE_MAX} anos. Vou te transferir para um consultor, que pode avaliar seu caso.`,
        )
      }
      if (cep) {
        return askAgain(
          { ...data, idade, cep },
          'plano',
          0,
          'Show! Qual plano te interessa: Essencial, Completo ou Premium?',
        )
      }
      return askAgain({ ...data, idade }, 'cep', 0, 'Obrigado! E qual o CEP de onde o carro fica guardado?')
    }

    case 'cep': {
      const cep = extractCep(leadText)
      if (cep === null) {
        if (attempts + 1 >= MAX_ATTEMPTS_PER_FIELD) {
          return handoff(
            data,
            attempts + 1,
            'Não consegui identificar um CEP válido pelo que você escreveu. Vou te transferir para um consultor te ajudar por aqui.',
          )
        }
        return askAgain(data, 'cep', attempts + 1, 'Não encontrei um CEP aí. Pode mandar no formato 01310-100?')
      }
      return askAgain(
        { ...data, cep },
        'plano',
        0,
        'Show! Qual plano te interessa: Essencial, Completo ou Premium?',
      )
    }

    case 'plano': {
      const planoId = extractPlano(leadText)
      if (planoId === null) {
        if (attempts + 1 >= MAX_ATTEMPTS_PER_FIELD) {
          return handoff(
            data,
            attempts + 1,
            'Não consegui identificar o plano escolhido. Vou te transferir para um consultor te ajudar por aqui.',
          )
        }
        return askAgain(
          data,
          'plano',
          attempts + 1,
          'Não peguei o plano. Escreva "Essencial", "Completo" ou "Premium".',
        )
      }
      if (data.veiculoAno === null || data.idade === null) {
        // Should not happen: earlier fields are validated before reaching this step.
        return handoff(data, 0, 'Faltou alguma informação no meio da conversa. Vou te transferir para um consultor.')
      }
      return {
        outcome: 'ready_to_quote',
        agentMessages: [],
        pendingField: 'done',
        data: { veiculoAno: data.veiculoAno, idade: data.idade, cep: data.cep, planoId },
        attempts: 0,
      }
    }

    case 'done':
      return askAgain(data, 'done', attempts, 'Esse atendimento já foi concluído.')
  }
}
