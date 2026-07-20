import { describe, expect, it } from 'vitest'
import {
  advanceConversation,
  buildQuote,
  extractCep,
  extractIdade,
  extractPlano,
  extractVeiculoAno,
  initialCollectedData,
  isIdadeAceita,
  isVeiculoAceito,
} from './offlineMockAgent'

describe('field extraction', () => {
  it('extracts age from free text', () => {
    expect(extractIdade('Tenho 35 anos')).toBe(35)
    expect(extractIdade('idade: 42')).toBe(42)
    expect(extractIdade('sem informação')).toBeNull()
  })

  it('extracts the vehicle year, preferring the last plausible year mentioned', () => {
    expect(extractVeiculoAno('Toyota Corolla 2008')).toBe(2008)
    expect(extractVeiculoAno('comprei em 2020, é um Onix 2019')).toBe(2019)
    expect(extractVeiculoAno('não sei o ano')).toBeNull()
  })

  it('extracts a CEP in either format', () => {
    expect(extractCep('cep 26703-384')).toBe('26703-384')
    expect(extractCep('meu cep e 01310100')).toBe('01310100')
    expect(extractCep('não tenho cep aqui')).toBeNull()
  })

  it('extracts the plano from keywords', () => {
    expect(extractPlano('quero o Premium')).toBe('premium')
    expect(extractPlano('o completo mesmo')).toBe('completo')
    expect(extractPlano('pode ser o essencial')).toBe('essencial')
    expect(extractPlano('não sei ainda')).toBeNull()
  })
})

describe('acceptance rules (mirrors quote-service plans.json)', () => {
  it('accepts ages between 18 and 75', () => {
    expect(isIdadeAceita(18)).toBe(true)
    expect(isIdadeAceita(75)).toBe(true)
    expect(isIdadeAceita(17)).toBe(false)
    expect(isIdadeAceita(76)).toBe(false)
  })

  it('accepts vehicles up to 20 years old', () => {
    expect(isVeiculoAceito(2024, 2026)).toBe(true)
    expect(isVeiculoAceito(2006, 2026)).toBe(true)
    expect(isVeiculoAceito(2005, 2026)).toBe(false)
  })
})

describe('buildQuote', () => {
  it('applies age, vehicle-age and region multipliers to the plan base price', () => {
    const quote = buildQuote('essencial', 35, 2022, '01310-100', 2026)
    expect(quote.premioMensal).toBeCloseTo(119.9 * 1.0 * 1.0 * 1.0, 2)
    expect(quote.franquia).toBe(4500)
    expect(quote.coberturas).toContain('roubo')
  })

  it('applies the high-risk region surcharge', () => {
    const quote = buildQuote('essencial', 35, 2022, '21000-000', 2026)
    expect(quote.premioMensal).toBeCloseTo(119.9 * 1.3, 2)
  })
})

describe('advanceConversation', () => {
  const baseData = initialCollectedData()

  it('walks the qualifying flow from vehicle year to a ready-to-quote outcome', () => {
    const afterVeiculo = advanceConversation({
      pendingField: 'veiculoAno',
      data: baseData,
      attempts: 0,
      leadText: 'Corolla 2018',
    })
    expect(afterVeiculo.pendingField).toBe('idade')

    const afterIdade = advanceConversation({
      pendingField: 'idade',
      data: afterVeiculo.data,
      attempts: 0,
      leadText: '35 anos, cep 01310-100',
    })
    expect(afterIdade.pendingField).toBe('plano')

    const afterPlano = advanceConversation({
      pendingField: 'plano',
      data: afterIdade.data,
      attempts: 0,
      leadText: 'Quero o completo',
    })

    expect(afterPlano.outcome).toBe('ready_to_quote')
    if (afterPlano.outcome === 'ready_to_quote') {
      expect(afterPlano.data).toEqual({ veiculoAno: 2018, idade: 35, cep: '01310-100', planoId: 'completo' })
    }
  })

  it('hands off when the vehicle is older than the accepted range', () => {
    const result = advanceConversation({
      pendingField: 'veiculoAno',
      data: baseData,
      attempts: 0,
      leadText: 'é um Gol 2000',
    })
    expect(result.outcome).toBe('handoff')
  })

  it('hands off when age is outside the accepted range', () => {
    const result = advanceConversation({
      pendingField: 'idade',
      data: { ...baseData, veiculoAno: 2020 },
      attempts: 0,
      leadText: 'tenho 80 anos',
    })
    expect(result.outcome).toBe('handoff')
  })

  it('hands off after repeated unparseable answers instead of looping forever', () => {
    const firstTry = advanceConversation({
      pendingField: 'veiculoAno',
      data: baseData,
      attempts: 0,
      leadText: 'não lembro',
    })
    expect(firstTry.outcome).toBe('ask')

    const secondTry = advanceConversation({
      pendingField: 'veiculoAno',
      data: baseData,
      attempts: firstTry.attempts,
      leadText: 'ainda não sei',
    })
    expect(secondTry.outcome).toBe('handoff')
  })
})
