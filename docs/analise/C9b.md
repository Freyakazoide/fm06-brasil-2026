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
- Libertadores/Sul-Americana: tabela abaixo ("CONMEBOL").

### CONMEBOL (conferido no código, 31/10)

Os `push` abaixo são iguais no original e no exe com todos os patches do mod (conferido
aplicando `EXE_PATCHES` à cópia original): dá para trocar no lugar, com o mesmo tamanho.

Libertadores (montagem `0x00C07980`; grupos em `0x00C05430`):

| Rodada | Setter | +0x40 | +0x44 | +0x48 | Imediatos |
|---|---|---|---|---|---|
| Preliminar (sorteio 15/1) | `0x00C07AC2` | 0 | 0 | 0 | `push ebx` ×3 (sem espaço para imm32) |
| Grupos | `0x00C07AFF` | £60.000 | £120.000 | 0 | `0x00C07AF3`, `0x00C07AEE` (não pagam por jogo; ficam como estão) |
| Grupos: entrada | `0x00C0570D` -> `0x00AC5490` | — | — | — | £300.000 a cada clube, tipo 3 ("Prêmios"), `0x00C05705` |
| Oitavas | `0x00C07F40` | 0 | 0 | £375.000 | `0x00C07F1A` |
| Quartas | `0x00C07FD5` | 0 | 0 | £425.000 | `0x00C07FCA` |
| Semifinal | `0x00C0807C` | 0 | 0 | £675.000 | `0x00C08071` |
| Final | `0x00C080F0` | £1.700.000 | £1.100.000 | 0 | `0x00C080E7`, `0x00C080E2` |

Hipótese descartada no jogo (31/10): o +0x40/+0x44 da rodada dos grupos **não** é prêmio
por empate/vitória (uma vitória por 3 a 0 não pagou nada). Para que serve, não se sabe.

Prêmio por jogo na fase de liga (conferido no código, 31/10): depois de cada jogo,
`0x00B0DE70` (método das vtables de fase de liga `0x01117F88`, `0x01125540`, `0x01125CF0`)
paga por `0x00B0B400` (finanças `[clube→0x00A18CD0]+0x118`, método 0x8C = "Prêmios em
Dinheiro", e notícia `0x0057ECF0`) os campos das regras da fase (`[fase+0x24]`, objeto de
0xA8 bytes, construtor `0x00B194A0`):
- `+0x30` ao vencedor (`0x00B0E160`);
- `+0x34` aos dois no empate (`0x00B0E1C4`);
- `+0x38` no outro ramo (`0x00B0E20F`), provavelmente derrota.
Os três começam em 0 no construtor (`0x00B1959E`…`0x00B195A4`), a montagem da Libertadores
(`0x00C07C25`…`0x00C07CE3`) não os grava, nenhum setter foi achado, e a leitura do save
(`0x00B10D10`) zera os três de novo (`0x00B10DFF`). A competição da fase está em
`[fase+0x18]` (é o que vai para a notícia em `0x00B0B499`). A vtable da Libertadores
`0x01154CF4` é gravada só no construtor (`0x00C06322`); a da Sul-Americana é `0x01154A3C`.
Procurado no código sem achar quem paga os grupos: `0x00B3EE40` (pagamento por rodada) só
é chamado pelo mata-mata (`0x00B485D0`), e as 12 chamadas de `0x00AC5490` são entradas
fixas de outras competições. O painel de regras (`0x00B6C910`, colunas 10 = "Per Win", 11
= "Per Draw", 22 = "Winner", 23 = "Loser") lê outra estrutura, não o +0x40/+0x44 da rodada.

Sul-Americana (montagem `0x00C07380`, com as rodadas do `sul_americana_2026`):

| Rodada (mod) | Setter | +0x40 | +0x44 | +0x48 | Imediatos |
|---|---|---|---|---|---|
| 1ª fase | `0x00C074A6` | 0 | £31.000 | 0 | `0x00C0747D` (só o perdedor) |
| 2ª fase | `0x00C0768A` | 0 | 0 | £31.000 | `0x00C0766E` |
| Oitavas | `0x00C076FA` | 0 | 0 | £50.000 | `0x00C076CE` |
| Quartas | `0x00C07825` | 0 | 0 | £100.000 | `0x00C07806` |
| Semifinal | `0x00C078C4` | 0 | 0 | £200.000 | `0x00C0789F` |
| Final | `0x00C07920` | £460.000 | £300.000 | 0 | `0x00C0790D`, `0x00C07908` |

Proposta de correspondência com a planilha (aba Premiacao, em dólar):
- Libertadores: entrada nos grupos = "Fase de grupos — participação" (US$ 1 mi); vitória
  nos grupos = US$ 340 mil e empate 0 (se a hipótese acima se confirmar); oitavas US$ 1,25
  mi, quartas US$ 1,7 mi, semifinal US$ 2,3 mi, vice US$ 7 mi, campeão US$ 25 mi. A
  preliminar (Fases 1–3) fica sem prêmio: não tem imediato para trocar no lugar.
- Sul-Americana: 1ª fase (perdedor) US$ 250 mil; 2ª fase = "Playoff" US$ 500 mil; oitavas
  US$ 600 mil, quartas US$ 700 mil, semifinal US$ 800 mil, vice US$ 2,5 mi, campeão US$ 10
  mi. A fase de grupos real não existe no mod.

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
  método **0x98** das finanças (+0x70, +0x104, +0x1CC; linha "Receitas Televisivas",
  conferido no jogo em 31/10) e manda a notícia
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
  (que cai em "Receitas Televisivas", ver 31/10) aos clubes da Série B, por uma tabela de UIDs (clube+0x14).
- 31/10, decidido: pagar a cota de 2026 da Série B no New Game. Patch `cota_serie_b_inicio`
  (`premiacao.first_quota_swaps`): o `ret` final do desvio do `patrocinio_inicio` vira
  `jmp .fm26+0x6110`; ali, com FINANCE+0x70 ainda 0, procura o UID do jogo do clube
  (`[esi+8]`+0x14) na tabela em +0x6160 (os 20 clubes "Série B" do
  `identidade_fm06.csv`, terminada em 0) e paga £2.933.071 (R$ 14,9 mi) pelo método 0x98
  das finanças. Teste com desmontagem ok (o teste pegou os saltos com 1 byte a menos).
  Instalado (`aplicar_tudo --rapido`): no `fm_brasil.exe` o `ret` virou `E9 E0000000` e a
  tabela tem os 20 UIDs (Goiás 102555). Falta ver no jogo.
- 31/10, New Game com o Goiás: **deu certo**. Finanças > Receitas no começo do save:
  "Receitas Televisivas" R$ 14,9M (Este Mês e Esta Época), "Patrocínio" R$ 17,99M,
  "Prêmios em Dinheiro" R$ 0, total R$ 32,89M. Conferido: o método **0x98** das finanças é a
  linha **"Receitas Televisivas"** (+0x70), não "Prêmios" (esse é o 0x8C, +0x60). Então a
  cota da temporada das ligas (`0x00AC5260`) é a receita de TV do jogo, e a cota da Série B
  ficou na linha certa. O "Receitas Televisivas" baixo do Flamengo (R$ 872 mil até maio) é
  porque a 1ª temporada não recebe a cota da Série A.
  Falta: ver em janeiro de 2027 se a cota cai de novo pelo caminho do jogo (uma vez só) e
  quanto a Série A recebe.
- 31/10, mesmo save do Goiás em 08/01/2027 (continua na Série B): **deu certo**, sem
  pagamento em dobro na temporada. Receitas:
  - "Última Época" (2026): "Receitas Televisivas" R$ 30,27M = R$ 14,9M do New Game (patch)
    + R$ 15,15M em dezembro de 2026 ("Último Mês": cota de R$ 14,9M + TV dos jogos). O
    total R$ 63,24M só fecha com a TV em milhões.
  - "Esta Época" (2027): TV R$ 12,69 mil, sem cota nova em janeiro.
  - Leitura: o jogo paga a cota quando a Série B monta a temporada **seguinte**, em
    dezembro (como o patrocínio, ficha C1b). A de 2027 caiu em dez/2026; a de 2026 o jogo
    nunca pagaria, e quem paga é o `cota_serie_b_inicio`. Uma cota por temporada.
    Hipótese: que o pagamento de dezembro venha de `0x00AC5260` (falta a notícia
    "Goiás recebe R$14.900.000" de dezembro). O valor bate.
  - Visto na mesma tela: "Patrocínio" R$ 17,99M em dezembro (Último Mês), mas "Última
    Época" R$ 17,99M e "Esta Época" R$ 0. O pagamento de dezembro não aparece em nenhuma
    das duas temporadas, só no saldo (Balance de ~R$ 50M para R$ 80,41M). Só aparência,
    não investigado.
  - Também na tela: orçamento de transferências recalculado na virada (R$ 21.426.611, 100%;
    ficha C5b) e empréstimo "R$13M - Banco (R$220m/mês até 30.7.2030)" do Goiás
    (empréstimos de 2005 do FINANCE_MANAGER, pendente).
- 31/10, patch `premiacao_conmebol_2026` (dólar a R$ 5,40, escolha do usuário): troca no
  lugar os 15 `push` da tabela CONMEBOL acima por US$ × 5,40 ÷ 5,08 em libras. Libertadores:
  entrada nos grupos US$ 1 mi (£1.062.992), vitória nos grupos US$ 340 mil no +0x44
  (£361.417), empate 0 no +0x40, oitavas US$ 1,25 mi, quartas US$ 1,7 mi, semifinal US$ 2,3
  mi, vice US$ 7 mi, campeão US$ 25 mi (£26.574.803). Sul-Americana: 1ª fase (perdedor)
  US$ 250 mil, playoff US$ 500 mil, oitavas US$ 600 mil, quartas US$ 700 mil, semifinal
  US$ 800 mil, vice US$ 2,5 mi, campeão US$ 10 mi. Testes: cada endereço é `push imm32`
  com o valor de 2005 antes da chamada ao setter (ou a `0x00AC5490`), os valores batem
  com a planilha e o patch aplica junto com todos os outros. Instalado
  (`aplicar_tudo --rapido`): no `fm_brasil.exe` os 15 `push` têm os valores novos (ex.:
  `0x00C080E7` = `68 D37F9501`, £26.574.803). Falta ver no jogo; hipótese a conferir:
  vitória = +0x44 nos grupos.
- 31/10, New Game com o Flamengo, resultado do `premiacao_conmebol_2026`:
  - Entrada nos grupos: **deu certo**. Notícia de 01/03/2026 "Flamengo recebe
    R$5.500.000 ... por disputar a Copa Libertadores da América do Sul - Fase de Grupos" (o
    valor pago é £1.062.992 = R$ 5,4 mi; a notícia arredonda, como na Copa).
  - Vitória nos grupos: **sem efeito**. Flamengo 3 x 0 UA Maracaibo em 05/04/2026 (Grupo
    C) e nenhum prêmio: "Prêmios em Dinheiro" de abril (Este Mês) R$ 0. Março (Último Mês)
    R$ 6,28M, temporada R$ 12,56M.
  - Leitura: o +0x40/+0x44 da rodada dos grupos não paga por jogo. O prêmio por jogo da
    fase de liga é outro campo (seção CONMEBOL acima), sempre 0 no jogo.
- 31/10, correção: o `premiacao_conmebol_2026` deixa o +0x40/+0x44 dos grupos como no
  original, e o novo patch `premio_vitoria_libertadores` troca a leitura do +0x30 em
  `0x00B0E160` (`8B4524 8B4830`) por `call` a um stub na .fm26+0x6200. O stub repete a
  leitura e, se a vtable da competição `[fase+0x18]` é `0x01154CF4`, devolve £361.417
  (US$ 340 mil a R$ 5,40). Como o valor está no código e não no objeto, vale também depois
  de carregar um save. Empate continua 0 (a planilha não tem prêmio por empate). Teste
  com desmontagem do stub ok. Instalado: no `fm_brasil.exe` `0x00B0E160` = `call
  0x015BA200 ; nop`, stub com `mov ecx, 0x583C9`, e os dois `push` dos grupos voltaram ao
  original. Falta ver no jogo.
- 31/10, New Game novo com o Flamengo, resultado do `premio_vitoria_libertadores`: **deu
  certo**. Notícia de 11/05/2026 "Flamengo recebe R$1.800.000 ... pela vitória sobre a
  Universidad de Chile na Copa Libertadores" (pago £361.417 = R$ 1.835.998; a notícia
  arredonda). 5 jogos nos grupos até 24/05. "Prêmios em Dinheiro": abril (Último Mês)
  R$ 5,5M = 3 × R$ 1,836M; maio (Este Mês) R$ 5,67M = 2 × R$ 1,836M + R$ 2M (hipótese: a 5ª
  fase da Copa do Brasil, que paga R$ 2 mi); temporada R$ 23,58M. Bate com 5 vitórias em 5
  jogos (a conferir em Calend. & Result.). Sem prêmio em empate ou derrota visto até
  aqui (não houve). Falta: save e carregar, e ganhar de novo.
