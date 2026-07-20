# Conversa completa — exemplo de resiliência real (não roteirizado)

_Gerada em 2026-07-19T00:46:55, real, contra o quote-service com as taxas de
instabilidade padrão (`QUOTE_FAILURE_RATE=0.20`, `QUOTE_SLOW_RATE=0.10`),
sem `QUOTE_SEED` — ou seja, a instabilidade abaixo não foi forçada._

Esta é a primeira execução da conversa de demonstração nesta sessão. Por
acaso, ela encontrou de forma orgânica os dois cenários que o desafio mais
valoriza: uma falha transitória (HTTP 500) seguida de um retry bem-sucedido,
**e** uma chamada lenta (~8s) que ainda assim teve sucesso e não foi
classificada como timeout. É mantida aqui como evidência adicional, junto
com `conversation-log.md` (a execução "limpa", sem falhas, usada como o
registro principal exigido pelo desafio).

**conversation_id**: `conv_e7220b51a6ab`

**Agente**: Oi! Aqui é da AutoSeguro 👋 Vou te ajudar a cotar o seguro do seu carro. Pra começar, me conta: qual o modelo e o ano do veículo?

**Lead**: Oi! Vi o anúncio de vocês, queria cotar o seguro do meu carro. Tenho um Corolla 2018.
**Agente**: Ótimo, Corolla 2018! E qual a sua idade?

_status da conversa: `collecting`_

**Lead**: Tenho 35 anos.
**Agente**: Perfeito! Agora, qual plano você gostaria: essencial, completo ou premium?

_status da conversa: `collecting`_

**Lead**: Meu CEP é 01310-100.
**Agente**: Legal! Só falta saber qual plano você escolheu: essencial, completo ou premium?

_status da conversa: `collecting`_

**Lead**: Quero o plano completo, por favor.
**Agente**: Consegui sua cotação no plano Completo! BRL 241.38/mês, franquia de BRL 3000.00. Coberturas: colisao, roubo, furto, terceiros, vidros. Carência de 30 dias para roubo, furto.

> Cotação estruturada: plano=completo, premio_mensal=241.38, franquia=3000.0, coberturas=['colisao', 'roubo', 'furto', 'terceiros', 'vidros'], carencia_dias=30, moeda=BRL

_status da conversa: `resolved`_

## Rastreabilidade (quote-attempts) — a parte interessante

```json
[
  {
    "quoteRequestId": "qreq_6734a185d4d7",
    "attemptNumber": 1,
    "status": "retrying",
    "httpStatus": 500,
    "errorClass": "http_500",
    "latencyMs": 60,
    "createdAt": "2026-07-19T03:47:04.561589Z"
  },
  {
    "quoteRequestId": "qreq_6734a185d4d7",
    "attemptNumber": 2,
    "status": "succeeded",
    "httpStatus": 200,
    "errorClass": null,
    "latencyMs": 8022,
    "createdAt": "2026-07-19T03:47:13.098471Z"
  }
]
```

A tentativa 1 recebeu um HTTP 500 simulado (`upstream_unavailable`) — exatamente
o caso que motiva tratar `http_500` como transitório neste projeto (ver
README, seção de decisões). A tentativa 2 demorou ~8 segundos (o branch de
lentidão simulada do quote-service) e ainda assim retornou uma cotação
válida — o `QUOTE_SERVICE_READ_TIMEOUT_SECONDS=15.0` configurado evitou que
essa chamada lenta-mas-bem-sucedida fosse classificada como falha, que é
exatamente a armadilha descrita no enunciado do desafio.

Nenhum preço foi exibido ao lead antes da tentativa 2 retornar com sucesso;
a mensagem final com o valor foi construída a partir do `QuoteResult` real
retornado pelo quote-service.
