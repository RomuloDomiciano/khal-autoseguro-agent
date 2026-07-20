import type { QuoteSummary } from '../types'

const currencyFormatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

interface QuoteCardProps {
  quote: QuoteSummary
}

export function QuoteCard({ quote }: QuoteCardProps) {
  return (
    <dl className="quote-card">
      <div className="quote-card__header">
        <dt className="chat-visually-hidden">Plano</dt>
        <dd className="quote-card__plano">{quote.planoNome}</dd>
        <dt className="chat-visually-hidden">Prêmio mensal</dt>
        <dd className="quote-card__premio">{currencyFormatter.format(quote.premioMensal)}/mês</dd>
      </div>

      <div className="quote-card__row">
        <dt>Franquia</dt>
        <dd>{currencyFormatter.format(quote.franquia)}</dd>
      </div>

      <div className="quote-card__row">
        <dt>Coberturas</dt>
        <dd>{quote.coberturas.join(', ')}</dd>
      </div>

      <div className="quote-card__row">
        <dt>Carência</dt>
        <dd>{quote.carenciaDias} dias para roubo e furto</dd>
      </div>
    </dl>
  )
}
