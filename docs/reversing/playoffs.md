# Playoffs e mata-matas (para as regras de 2026)

## Desempate pela melhor campanha

O motor já tem a regra que a Série B de 2026 usa ("empate nos dois jogos:
sobe quem fez melhor campanha"). Textos em `.rdata`:

- `0x0109D2E0` "<%team#1-short> win if scores are still level, due their higher league position"
- `0x0109D280` "... level after ninety minutes, due their higher league position"
- `0x0109D388` "... still level, due to higher seeding"

Quem escolhe o texto: `0x006A1F2C`, que lê uma palavra de flags do confronto
(`+0x94`): bit `0x100` = vence a melhor posição na liga; bit `0x40` = vence o
melhor cabeça de chave. Falta achar onde a montagem da fase liga esses bits
(candidatos: `0x00B3BB10` / `0x00B3BAD0`, chamados na montagem do mata-mata
da antiga Série C, `0x00BC0143`–`0x00BC0449`).

Outras pistas: `LEAGUE_STAGE::check_for_position_playoff()` (`0x00B13301`),
"Fifth Placed Playoff" (`0x009F7C3C`).

## Plano

| Regra de 2026 | Ideia |
|---|---|
| Série B: 3º×6º e 4º×5º, ida e volta, sem pênaltis, vence a melhor campanha | 2ª fase na Série B: mata-mata de 4, uma rodada, bit `0x100`; vencedores sobem com o 1º e o 2º |
| Série C: grupos B (1,4,5,8) e C (2,3,6,7), ida e volta; final ida e volta com pênaltis | 2ª e 3ª fases na nova C; achar como o jogo semeia grupos pela posição |
| Série D: 6 acessos | refazer o mata-mata da antiga C |

## Modelos no próprio FM06

| Liga | Montagem | O que tem |
|---|---|---|
| Championship (ID 12) | `0x00C15480` | fase de liga com `+0x11 = 2` (sobem), `+0x12 = 4` (zona de playoff 3º–6º), `+0x14 = 3`; ação `0x00B0FF00(2, {0x01117604, 0x011175F8, 0x15, -1})` liga a zona à fase de código 0x15; fase 2: mata-mata de 4 (`0x00B480D0`), semifinal (rodada 0x12) e final (0x14) |
| Série B italiana (ID 0x21) | `0x00C0FAC0` | fase 2 igual, mas a configuração do 2º jogo da semifinal grava `0x100` (desempate pela posição na liga) |

Destinos no fim do mata-mata: `0x00B46860(rodada, 0 = vencedor / 1 = perdedor, destino)`,
com o destino vindo do método 4 da competição (`1` = divisão de cima, `6` = fica).

Número de fases da competição: argumento de `0x00AC24F0` no construtor (Série B: 1).

## Patch `serie_b_playoffs`

- Construtor da Série B: 2 fases.
- Fase 1 (liga): desvio em `0x00BBA7B6` grava `+0x12 = 4` e chama a ação
  `0x00B0FF00(2, …0x15…)`, como na Championship.
- Método 71 da vtable da Série B → despachante: fase 1 vai para uma cópia da
  montagem italiana (área livre `0x00E30760`), as outras para a original.
- Na cópia: sem final (vencedores da semifinal sobem), sorteio 16/11, 1º jogo
  21/11, 2º jogo uma semana depois.
- A fase de pontos corridos da Série B termina em 15/11 (`serie_b_datas_2026`).

## Como uma fase passa times para a seguinte

Pelas ligas que já funcionam (Championship, Série B italiana, antiga Série C):

- zona 1 (`+0x11`) **sem** ação = sobe de divisão (destino na regra
  `0x00B0FE50`, declarada na 1ª fase);
- zona 1 com a ação `0x00B0FF00(5, {…, nome, -1})` = classifica para a fase
  seguinte (grupos da antiga C → mata-mata);
- zona 2 (`+0x12`) com a ação `0x00B0FF00(2, {…, nome, -1})` = playoff
  (Championship). O "nome" é o nome da fase (`0x00B4BE40`: 0x15 Playoff,
  0x49 fase de grupos, 0xA7 fase final, 0x12/0x14 semifinal/final).
- Mata-mata → fase seguinte: `0x00B45500(rodada, 0, {…, nome, -1})`.

## Série C em fases (`serie_c_nova`)

- Seção nova `.fm26` (RVA `0x011B4000`, 64 KB, código) no fim do arquivo.
- Vtable da nova C, método 71 → despachante (`0x015B4000`): fase 0 → cópia da
  B (liga de 20, turno único, zona 1 = 8 com ação 5 "fase de grupos", 2 caem);
  fase 1 → cópia da montagem da antiga C (`0x015B4100`) chamada como fase 0:
  2 grupos de 4, ida e volta, zona 1 = 2 sobem (sem ação), sem regras próprias.
- Construtor da nova C: 2 fases.

## Série D com 6 acessos (`serie_d_96`)

Mata-mata da antiga C sem a 3ª rodada (salto em `0x00BC037C`); os vencedores
da 2ª rodada (`0x00B45500(8, …)`) vão para a fase final, agora com 8 clubes
em turno único (`0x00BC04E0`, `0x00BC054C`) e 6 acessos (`0x00BC0573`).
