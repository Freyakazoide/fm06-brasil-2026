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
- 29/10: a tela da Copa do Brasil no jogo não mostra prêmio em dinheiro. "Prêmios" são os
  individuais (artilheiro) e no começo do save a Copa ainda não tem calendário. A
  conferência fica pelas finanças ("Prêmios em Dinheiro").
- 29/10, patch `premiacao_copa_2026` (`premiacao.py`): os `push imm32` das cópias da
  montagem feitas pelo `copa_do_brasil_2026` (fase 1 em `.fm26`+0x3000, fase 2 em +0x3400)
  com os valores da CBF de 2026 em libras (÷ 5,08):
  3ª fase R$ 1,53 mi e 4ª R$ 1,68 mi (Grupo II), 5ª R$ 2 mi, oitavas R$ 3 mi, quartas
  R$ 4 mi, semifinal R$ 9 mi, vice R$ 34 mi, campeão R$ 78 mi. Testes ok. Instalado (`aplicar_tudo --rapido`):
  no `fm_brasil.exe` os 8 `push` estão com os valores novos (5ª fase £393.701 = R$ 2 mi,
  campeão £15.354.331 = R$ 78 mi). Falta ver no jogo.
- 29/10, New Game com o Flamengo: **deu certo**. Notícia de 31/05/2026 "Flamengo recebe
  R$2.000.000 ... por disputar a Copa do Brasil", depois de "Flamengo vence na Copa do
  Brasil - 2ª Elim." (a 5ª fase do mod usa o código de rodada 7). Receitas: "Prêmios em
  Dinheiro" Este Mês R$ 2M; Esta Época R$ 10,9M (já no começo, origem ainda não achada)
  -> R$ 15,31M. Conferido: o +0x48 é pago **uma vez por confronto** (ida e volta não paga
  duas vezes) e cai em "Prêmios em Dinheiro". Falta ver a final (+0x40/+0x44).
- Visto na mesma tela: "Receitas Televisivas" R$ 872 mil na temporada até maio (Flamengo),
  muito abaixo das cotas reais (aba Cotas_TV).

## Cota da temporada das ligas (conferido no código, 29/10)

- `0x00AC5260` (chamado só por `0x00ACDAD0`, que é chamado por `0x00C4BD21`): para cada
  clube da tabela da competição (+0xA4; lista +0x2C, quantidade +0x34), pede o valor ao
  método **0x128** (slot 74) da competição e, se for > 100 (`0x00AC52F3`), paga pelo
  método **0x98** das finanças (+0x70, +0x104, +0x1CC) e manda a notícia
  `COMP_PRIZE_MONEY_NEWS`. Não paga quando o ano da competição (+0x9C) é 2005
  (`0x00AC52AF`).
- Slot 74 das classes do Brasil:
  - Série A (vtable `0x0113B2FC`, slot em `0x0113B424`): `0x00BB2D90`, pela reputação do
    clube (`0x00A2A570`): > 6500 £4.000.000, > 5500 £2.000.000, senão £1.000.000.
  - Série B (`0x0113B5B4`, slot `0x0113B6DC`): `0x00B845A0` = `mov eax, 250000 ; ret 4`
    (£250 mil = R$ 1,27 mi), função também das vtables `0x0112AF2C` e `0x011518F4`.
  - Série C, Copa e estaduais: `0x00AC2310` (base: 0 quando +0xB8 não é 0).
- Hipótese: é o dinheiro de "Prêmios em Dinheiro" que aparece logo no começo do save
  (Flamengo R$ 10,9 mi; £2 mi = R$ 10,16 mi da Série A + outro valor ainda não achado).
- Patch `cota_serie_b_2026`: slot `0x0113B6DC` -> `.fm26`+0x6100 `B8 4FC12C00 C20400`
  (£2.933.071 = R$ 14,9 mi, aba Cotas_TV). Testes ok; instalado (`aplicar_tudo --rapido`,
  slot = `0x015BA100` no `fm_brasil.exe`). Falta ver no jogo.
- A Série A fica como está até ter os valores de 2026 por clube (a aba Cotas_TV só tem a
  Série B).
- 29/10, New Game com o Goiás (Série B): "Prêmios em Dinheiro" R$ 0 no New Game e em
  03/01/2026. A cota **não** é paga no começo do save: a hipótese do momento estava errada.
  `0x00ACDAD0` é um método comum a todas as competições (está em ~300 vtables) e chama
  `0x00AC5260` no meio da montagem da temporada da competição. Nova hipótese: a cota cai na
  virada de temporada da própria competição (Série A: construtor grava +0x85 = 3, abril).
  Os R$ 10,9 mi do Flamengo no New Game vêm de outro lugar (Goiás, sem Libertadores, teve
  R$ 0).
- 29/10, mesmo save do Goiás em 02/05/2026: **sem efeito** para a cota da Série B (ela já
  começou em 21/3). "Prêmios em Dinheiro" Esta Época R$ 3,21M = só a Copa: notícia de
  22/03 "Goiás recebe R$1.500.000 ... por disputar a Copa do Brasil" (depois da "1ª Elim.",
  a 3ª fase: R$ 1,53 mi, a notícia arredonda) e Último Mês (abril) R$ 1,68M (4ª fase). As
  cotas da 3ª e da 4ª fase da Copa (Grupo II) estão **conferidas no jogo**.
- Quando a cota roda (conferido no código): `0x00ACDAD0` é o slot **0x248** das vtables de
  competição (Série B `0x0113B7FC`, Série A `0x0113B544`), a montagem da temporada nova.
  - Na criação do jogo (`0x00AE2AFB` -> `0x00AD4590`), para cada competição da nação: com
    +0xB4 = -1 (sem data marcada, padrão do construtor base em `0x00ACF4F5`; a Série B usa
    o base) chama o slot 0x248 na hora (`0x00AD46CA`); com data no futuro, só agenda
    (método 0x118).
  - Antes disso, `0x00AD00C0` grava o ano da temporada da nação: 2006 se o início do mundo
    for **depois** da virada da nação (`setg` em `0x00AD016E`), senão 2005. Com a virada
    do Brasil em 1/1 (`virada_1_janeiro`) e o jogo começando em 1/1, o ano fica 2005 e
    `0x00AC5260` pula (hipótese forte: explica o R$ 0 do Goiás). É o mesmo do jogo
    original: a 1ª temporada do save não recebe cota.
  - Mesmo que pagasse ali, cairia nas finanças **básicas**: a criação (`0x00463613`) vem
    antes do FINANCE_MANAGER (`0x004636D4`) e da troca para as completas. O método 0x98 das
    básicas (`0x00A287A0`) só soma no saldo, sem linha de receita, e o init das completas
    sorteia o saldo de novo.
  - Hipótese: a próxima cota cai na montagem da temporada de 2027 (virada de janeiro).
- Consequência: para a cota de 2026 aparecer, ela tem que ser paga no init das finanças do
  New Game, como o `patrocinio_inicio` (desvio em `.fm26`+0x6000): pelo método 0x98
  ("Prêmios em Dinheiro") aos clubes da Série B, por uma tabela de UIDs (clube+0x14).
