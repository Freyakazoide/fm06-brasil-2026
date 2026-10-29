# Ficha C9b — Premiação das competições (de onde vem o valor)

- Quem analisou / data: Claude, 2026-10-29 (capstone + pefile, `fm.exe` 6.0.2 original)
- Pergunta (docs/ANALISE_DE_CODIGO.md): quem cria a notícia `COMP_PRIZE_MONEY_NEWS`
  (construtor `0x00747D90`) e de onde vem o valor do prêmio.

## Conferido no código

### Quem paga

- O construtor da notícia é chamado por seis funções. Uma é a fábrica do carregador
  (`0x0074EE90`, tipo 0x16); as outras montam a notícia e pagam:
  - **`0x00AC5490`** (thiscall na competição; args: time, valor £, tipo, ...): chama
    `0x00A18CD0` (clube do time), CLUB+0x118 (finanças) e soma o valor pelo método
    `0x8C` (tipo diferente de 0 e de 8) ou `0x98` (tipo 0 ou 8). Depois monta e entrega
    a notícia (`0x0057ECF0`, `0x00753C10`).
  - **`0x00B3EE40`** (genérico das fases): mesmo pagamento pelo método `0x8C`, com a
    notícia.
- Chamadas de `0x00AC5490` por país (pelas funções exportadas vizinhas): UEFA
  (`0x00B60D70`…`0x00B63E00`), Irlanda (`0x00BB0260`), Turquia (`0x00BC5200`,
  `0x00BC5390`), CONMEBOL (`0x00C05430`) e AFC (`0x00C1A350`, `0x00C1A740`,
  `0x00C1BD90`, com valores fixos £20.000, £15.000 e £51.813). **Nenhuma no código do
  Brasil.**

### Prêmio por rodada de mata-mata (genérico)

- Depois de cada jogo de mata-mata, `0x00B485D0` lê a rodada (`edi`, objeto da lista
  `[fase+0x1C]+0xC`) e paga com `0x00B3EE40`:
  - `+0x48` aos **dois** clubes (tipo 3, `0x00B48B18`…`0x00B48B42`);
  - `+0x40` a um clube (tipo 4, `0x00B48B47`);
  - `+0x44` ao outro (tipo 5, `0x00B48B64`).
  Hipótese: +0x48 = cota por participar da rodada, +0x40 = vencedor, +0x44 = perdedor.
  Os títulos do painel de regras da fase (`0x01124320` "Winner Prize Money",
  `0x011242D8` "Loser Prize Money", `0x011243B0` per win, `0x01124368` per draw;
  `0x00B6CA98`…) batem com isso.
- Quem grava: **`0x00B3BA80`** `(+0x40, +0x44, +0x48)`, setter chamado 416 vezes pelas
  classes de competição, sempre com `push` imediato. Não vem do `server_db`.
- Valor padrão: `0x00B3FB20` (chamado por `0x00B441FC`) põe prêmio na **última rodada**
  quando ela não tem `+0x40` nem `+0x48`: £1.000.000, £500.000, £100.000, £30.000 ou
  £10.000, conforme `[fase+0x18]+0x70` (≥16, ≥12, ≥8, ≥4, menor).

### Copa do Brasil (classe `0x00BB30F0`, método 71 = `0x00BBAD30`)

- `0x00BBAD30` está no slot 71 da vtable `0x0113BB24` (gravada pelo construtor
  `0x00BB30F0` em `0x00BB3133`), o mesmo método de "montagem das fases" da Série A.
- Rodadas montadas com `0x00B3BA80` (args na ordem +0x40, +0x44, +0x48; o `push` do
  +0x48 vem primeiro):

  | Chamada | Rodada | +0x40 venc. | +0x44 perd. | +0x48 os dois | Onde está o imediato |
  |---|---|---|---|---|---|
  | `0x00BBADFD` | modelo (`[esp+0x4A]`=0xE) | 0 | 0 | 0 | `push ebx` ×3 |
  | `0x00BBAE67` | 1ª fase (32 jogos) | 0 | 0 | £8.000 | `0x00BBAE38` `68 401F0000` |
  | `0x00BBAEE2` | 2ª fase | 0 | 0 | £8.000 | `0x00BBAED7` `68 401F0000` |
  | `0x00BBAF5C` | oitavas (16→8) | 0 | 0 | £26.000 | `0x00BBAF34` `68 90650000` |
  | `0x00BBAFD3` | quartas (8→4) | 0 | 0 | £33.000 | `0x00BBAFAE` `68 E8800000` |
  | `0x00BBB03A` | semifinal (4→2) | 0 | 0 | £44.000 | `0x00BBB017` `68 E0AB0000` |
  | `0x00BBB0A2` | final (2→1) | £200.000 | £100.000 | 0 | `0x00BBB081` `68 400D0300`, `0x00BBB07C` `68 A0860100` |

  Em reais (× 5,08): 1ª fase R$ 40,6 mil, final R$ 1,016 mi ao campeão. A cota real de
  2026 (`premiacao_2026.xlsx`) vai de R$ 400 mil (1ª fase) a R$ 78 mi (campeão).
- Libertadores/Sul-Americana: 14 chamadas do setter no código `sam_` (`0x00C04562`…
  `0x00C07FD5`) e a rotina própria `0x00C05430`; falta a tabela.

## Hipótese / não conferido

- Que +0x40 vai ao vencedor e +0x44 ao perdedor (falta ver no jogo).
- Ligas (Séries A–D): nenhuma chamada do setter nem de `0x00AC5490` no código do Brasil.
  Os "Prêmios em Dinheiro" de janeiro (R$ 4,7 mi e R$ 6,27 mi no Flamengo, ficha C1b)
  vêm de outro lugar, ainda não achado.
- Cotas de TV: não procuradas ainda.

## Consequência

A premiação da Copa do Brasil é trocável por patch no exe, só nos imediatos acima, com o
mesmo tamanho (`push imm32`). O formato da CBF cabe: cota por fase para os dois clubes
(+0x48 da 1ª fase à semifinal) e campeão/vice (+0x40/+0x44 da final). Não cabe a
diferença entre Grupo II e Grupo III da 1ª à 4ª fase (o jogo tem um valor por rodada).
Os zeros usam `push ebx` (1 byte) e não precisam mudar.

Falta conferir no jogo se o +0x48 é pago uma vez por confronto ou uma vez por jogo
(ida e volta pagaria duas vezes). Ficam para a próxima etapa a tabela da CONMEBOL, o
prêmio das ligas e as cotas de TV.

## Diário

- 29/10: leitura do código (acima); nenhum teste no jogo ainda.
