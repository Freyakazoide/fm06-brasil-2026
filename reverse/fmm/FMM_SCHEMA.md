# FMM2 6.0.2f72973 — schema vivo preliminar

## Resumo

Campos confirmados: 17 campos pessoais, 13 offsets Playing, 13 campos de contrato, 4 bits de Preferred Moves, 1 campo de clube, 3 campos de nação e a seleção da terceira linha de raízes do FMM2.

Campos high confidence: 75 entradas adicionais. A transformação numérica de leitura não está confirmada para todos os atributos Playing.

Campos unresolved: 31 entradas explícitas nos artefatos.

Hipóteses rejeitadas: endereços absolutos estáveis; primeira ocorrência do UID; PA de database menos 1; UID público igual a ID interno de clube/nação; ano literal como formato de contrato.

## Fonte e build

- FMM usado: `C:\Games\Programas\FMM2\FMM.txt`
- SHA-256: `90f86dd6f4efefecdd29bacc8c86f6201a59a423769aa724834222e2ea3c0aea`
- Build: `fm.exe` 6.0.2f72973
- Linha ativa: terceira linha (índice 2). A prova é estrutural: os marcadores `[Player]` `010F1034 010F1020 010F0FF8 010F0FEC 010F0FD8` aparecem consecutivos em `UID-20..UID-4`, e `010F12F4 010F14CC` em `UID-224..UID-220`.

## Player object

Stride observado: 456 bytes. O UID fica em `record_start+224`. Não usar endereço absoluto.

| Campo | Offset relativo ao UID | Tipo | Evidência | Confiança |
|---|---|---|---|---|
| Nationality | 64 | pointer -> Nation record | Diff Argentina UID 1649→Espanha UID 796 trocou o ponteiro entre os dois objetos Nation válidos. | CONFIRMED |
| Born | 52 | Date {u16 day_of_year_0, u16 year} | 11/12/1981→12/12/1981 alterou dia 344→345 em UID+52. | CONFIRMED |
| Value |  |  | Candidato u32 em UID-196 apareceu apenas numa alteração acidental da restauração; não promovido. | UNRESOLVED |
| Ask Value | -192 | u32 | Alteração isolada 6350936→6350937. | CONFIRMED |
| Current Ability | -204 | u16 | Saviola 160→161; mesmo offset em Zidane, Ceni, Sávio e Fred. | CONFIRMED |
| Potential Ability | -202 | u16 | Saviola 179→178; mesmo offset estrutural nos demais âncoras. | CONFIRMED |
| Height | -76 | u16 | Diff manual Saviola 168→169; Zidane 185 no mesmo offset. | CONFIRMED |
| Weight | -78 | u16 | Diff manual Saviola 61→62; Zidane 80 no mesmo offset. | CONFIRMED |
| Home Rep. | -210 | u16 | Diff manual Saviola 8198→8197. | CONFIRMED |
| Current Rep. | -208 | u16 | Diff manual Saviola 7998→7997. | CONFIRMED |
| World Rep. | -206 | u16 | Diff manual Saviola 5862→5861. | CONFIRMED |
| Int. Caps | 72 | u8 | Saviola 29 e Zidane 95 exatos na ficha viva. | HIGH |
| Int. Goals | 74 | u8 | Saviola 1 e Zidane 26 exatos na ficha viva. | HIGH |
| U21 Caps | 73 | u8 | Alteração isolada 0→1 em UID+73. | CONFIRMED |
| U21 Goals | 75 | u8 | Alteração isolada 0→1 em UID+75. | CONFIRMED |
| Morale | -184 | u8 | Diff manual Saviola 20→19. | CONFIRMED |
| Fitness | -216 | u16 | Diff manual Saviola 4000→3999. | CONFIRMED |
| Jadedness | -212 | u16 | Diff manual Saviola 0→1. | CONFIRMED |
| Match Exercise | -214 | u16 | Diff manual Saviola 7080→7079. | CONFIRMED |

## Personal Info / PData

O registro PData tem stride 36, assinatura de 20 bytes, UID em `+20` e oito bytes de personalidade em `UID+8..+15`.

| Campo | Offset relativo ao UID PData | Tipo | Evidência | Confiança |
|---|---|---|---|---|
| Adaptability | 8 | u8 | Diff manual Saviola 12→13; sequência PData coerente. | CONFIRMED |
| Ambition | 9 | u8 | Sequência FMM completa. | HIGH |
| Loyalty | 10 | u8 | Sequência FMM completa; FMM também contém typo Loyality. | HIGH |
| Pressure | 11 | u8 | Sequência FMM completa. | HIGH |
| Professional | 12 | u8 | Sequência FMM completa. | HIGH |
| Sportsmanship | 13 | u8 | Sequência FMM completa. | HIGH |
| Temperament | 14 | u8 | Sequência FMM completa. | HIGH |
| Controversy | 15 | u8 | Sequência FMM completa. | HIGH |

## Playing attributes

O registro Playing tem stride 112, assinatura em `UID-20..-4` e 79 bytes em `UID+8..UID+86`. A ordem lógica é resolvida pela permutação `[Playing Position]` do FMM2. Cada linha está em `playing_attributes_layout.json`.

Os campos posicionais (índices FMM 54–78) aparecem diretamente em escala 1–20. Os atributos restantes incluem valores raw 0–255. A rodada manual confirmou que o FMM2 grava um literal u8 nos campos editados, mas a transformação dos valores originais carregados do save continua sem fórmula geral.

| Índice FMM | Campo | Índice físico | Offset UID | Tipo | Raw Saviola | Confiança offset |
|---|---|---|---|---|---|---|
| 0 | Crossing | 25 | 33 | u8 | 247 | CONFIRMED |
| 1 | Dribbling | 26 | 34 | u8 | 11 | CONFIRMED |
| 2 | Finishing | 27 | 35 | u8 | 247 | CONFIRMED |
| 3 | Heading | 28 | 36 | u8 | 227 | HIGH |
| 4 | Long Shots | 29 | 37 | u8 | 242 | HIGH |
| 5 | Marking | 30 | 38 | u8 | 207 | HIGH |
| 6 | Passing | 32 | 40 | u8 | 242 | HIGH |
| 7 | Tackling | 34 | 42 | u8 | 207 | HIGH |
| 8 | First Touch | 47 | 55 | u8 | 11 | HIGH |
| 9 | Technique | 48 | 56 | u8 | 16 | HIGH |
| 10 | Penalty | 33 | 41 | u8 | 81 | CONFIRMED |
| 11 | Corner | 52 | 60 | u8 | 76 | HIGH |
| 12 | Set Pieces | 60 | 68 | u8 | 61 | HIGH |
| 13 | Throwing | 55 | 63 | u8 | 56 | HIGH |
| 14 | Creativity | 35 | 43 | u8 | 252 | CONFIRMED |
| 15 | Anticipation | 42 | 50 | u8 | 252 | CONFIRMED |
| 16 | Decision | 43 | 51 | u8 | 242 | HIGH |
| 17 | Positioning | 45 | 53 | u8 | 222 | HIGH |
| 18 | Off the ball | 31 | 39 | u8 | 1 | HIGH |
| 19 | Composure | 77 | 85 | u8 | 252 | HIGH |
| 20 | Concentration | 78 | 86 | u8 | 252 | HIGH |
| 21 | Flair | 51 | 59 | u8 | 80 | HIGH |
| 22 | Influence | 65 | 73 | u8 | 56 | HIGH |
| 23 | Dirtiness | 66 | 74 | u8 | 25 | HIGH |
| 24 | Bravery | 68 | 76 | u8 | 31 | HIGH |
| 25 | Consistency | 69 | 77 | u8 | 60 | HIGH |
| 26 | Aggression | 70 | 78 | u8 | 20 | CONFIRMED |
| 27 | Imp. match | 72 | 80 | u8 | 70 | HIGH |
| 28 | Versatility | 74 | 82 | u8 | 50 | HIGH |
| 29 | Determination | 76 | 84 | u8 | 75 | HIGH |
| 30 | Team work | 53 | 61 | u8 | 61 | HIGH |
| 31 | Work rate | 54 | 62 | u8 | 56 | HIGH |
| 32 | Acceleration | 59 | 67 | u8 | 96 | CONFIRMED |
| 33 | Strength | 61 | 69 | u8 | 31 | HIGH |
| 34 | Stamina | 62 | 70 | u8 | 76 | HIGH |
| 35 | Pace | 63 | 71 | u8 | 86 | CONFIRMED |
| 36 | Jumping | 64 | 72 | u8 | 36 | HIGH |
| 37 | Balance | 67 | 75 | u8 | 56 | HIGH |
| 38 | Injury prone. | 73 | 81 | u8 | 40 | HIGH |
| 39 | Natural fit. | 75 | 83 | u8 | 50 | HIGH |
| 40 | Agility | 71 | 79 | u8 | 96 | HIGH |
| 41 | Left foot | 49 | 57 | u8 | 56 | CONFIRMED |
| 42 | Right foot | 50 | 58 | u8 | 100 | HIGH |
| 43 | Handling | 36 | 44 | u8 | 186 | CONFIRMED |
| 44 | Aer ability | 37 | 45 | u8 | 186 | HIGH |
| 45 | Cmd of area | 38 | 46 | u8 | 186 | HIGH |
| 46 | Communiction | 39 | 47 | u8 | 201 | HIGH |
| 47 | Kicking | 40 | 48 | u8 | 191 | HIGH |
| 48 | Long throws | 41 | 49 | u8 | 191 | HIGH |
| 49 | One on one | 44 | 52 | u8 | 201 | HIGH |
| 50 | Reflexes | 46 | 54 | u8 | 179 | HIGH |
| 51 | Eccentricity | 56 | 64 | u8 | 35 | HIGH |
| 52 | Rushing out | 57 | 65 | u8 | 75 | HIGH |
| 53 | Punch | 58 | 66 | u8 | 80 | HIGH |
| 54 | Goalkeeper | 0 | 8 | u8 | 1 | HIGH |
| 55 | Sweeper | 1 | 9 | u8 | 1 | HIGH |
| 56 | Defender | 2 | 10 | u8 | 1 | HIGH |
| 57 | Def. Mid. | 3 | 11 | u8 | 1 | HIGH |
| 58 | Midfielder | 4 | 12 | u8 | 8 | HIGH |
| 59 | Att. Mid. | 5 | 13 | u8 | 17 | CONFIRMED |
| 60 | Attacker | 6 | 14 | u8 | 20 | CONFIRMED |
| 61 | Wing back | 7 | 15 | u8 | 1 | HIGH |
| 62 | Free role | 8 | 16 | u8 | 18 | HIGH |
| 63 | Right side | 9 | 17 | u8 | 17 | HIGH |
| 64 | Left side | 10 | 18 | u8 | 12 | HIGH |
| 65 | Center side | 11 | 19 | u8 | 20 | HIGH |
| 66 | Left Def. | 12 | 20 | u8 | 1 | HIGH |
| 67 | Center Def. | 13 | 21 | u8 | 1 | HIGH |
| 68 | Right Def. | 14 | 22 | u8 | 1 | HIGH |
| 69 | Def. C.M. | 15 | 23 | u8 | 1 | HIGH |
| 70 | Mid. Left | 16 | 24 | u8 | 8 | HIGH |
| 71 | Mid. Center | 17 | 25 | u8 | 1 | HIGH |
| 72 | Mid. Right | 18 | 26 | u8 | 8 | HIGH |
| 73 | Att. M.L. | 19 | 27 | u8 | 12 | HIGH |
| 74 | Att. M.C. | 20 | 28 | u8 | 1 | HIGH |
| 75 | Att. M.R. | 21 | 29 | u8 | 17 | HIGH |
| 76 | Att. Center | 22 | 30 | u8 | 20 | HIGH |
| 77 | Wing B.L. | 23 | 31 | u8 | 1 | HIGH |
| 78 | Wing B.R. | 24 | 32 | u8 | 1 | HIGH |

## Contract

As raízes `00EB3954` e `010BAAD4` formam registros de 120 bytes (contrato principal) e 72 bytes (empréstimo). Em ambos, `+4` aponta para `Player UID-20` e `+8` aponta para o início do objeto Club. O contrato principal e o empréstimo de Saviola foram ligados sem depender de endereço absoluto.

`Started` e `Expires` ficam em `+24` e `+32`, como `{u16 dia_do_ano_base_zero, u16 ano}`. O cruzamento reproduz exatamente datas de Zidane, Ceni, Sávio e Saviola, e os diffs de um dia confirmaram ambos. `Wages` fica em `+16`; a edição manual 650001 foi gravada como o tagged integer `650001*10+2 = 6500012`. Os testes 17–28 foram aplicados ao contrato principal do Barcelona apesar do roteiro mencionar Sevilla; a ligação do ponteiro de clube torna esse desvio explícito e os diffs isolados continuam válidos para o layout comum.

| Índice FMM | Campo | Offset | Tipo | Confiança |
|---|---|---|---|---|
| 0 | Club | 8 | pointer -> Club record | HIGH |
| 1 | Wages | 16 | tagged u32: value*10+2 | CONFIRMED |
| 2 | Started | 24 | Date {u16 day_of_year_0, u16 year} | CONFIRMED |
| 3 | Expires | 32 | Date {u16 day_of_year_0, u16 year} | CONFIRMED |
| 4 | Squad Status | 37 | enum u8 | CONFIRMED |
| 5 | Transfer | 38 | flags u8 (semântica dos bits parcial) | CONFIRMED |
| 6 | Loan | 38 | flags u8; bit 1 observado | CONFIRMED |
| 7 | Unhappy |  |  | UNRESOLVED |
| 8 | Happiness | 48 | u8 | CONFIRMED |
| 9 | Squad Number | 49 | u8; 0xFF = ausente, transformação de entrada pendente | CONFIRMED |
| 10 | Apears | 76 | u32 | CONFIRMED |
| 11 | Goal | 80 | u32 | CONFIRMED |
| 12 | Assist | 84 | u32 | CONFIRMED |
| 13 | Clean Sheet | 88 | u32 | CONFIRMED |
| 14 | Mini Release |  |  | UNRESOLVED |
| 15 | Agreed Price | 56 | signed u32; -1 = ausente | CONFIRMED |

## Preferred Moves

Os 48 nomes foram preservados em ordem. O armazenamento é um bitset de 48 bits em `Player UID-48..UID-43`, LSB-first. Os índices 0, 1, 31 e 47 tiveram diffs controlados; os demais bits são interpolação estrutural `HIGH`. Dois textos portugueses visíveis continuam semanticamente ambíguos, sem afetar o mapa físico.

| Índice FMM | Movimento | Offset | Bit | Confiança |
|---|---|---|---|---|
| 0 | Runs With Ball Down Left | -48 | 0 | CONFIRMED |
| 1 | Runs With Ball Down Right | -48 | 1 | CONFIRMED |
| 2 | Runs With Ball Through Centre | -48 | 2 | HIGH |
| 3 | Gets Into Opposition Area | -48 | 3 | HIGH |
| 4 | Moves Into Channels | -48 | 4 | HIGH |
| 5 | Gets Forward Whenever Possible | -48 | 5 | HIGH |
| 6 | Plays Short Simple Passes | -48 | 6 | HIGH |
| 7 | Tries Killer Balls Often | -48 | 7 | HIGH |
| 8 | Shoots From Distance | -47 | 0 | HIGH |
| 9 | Shoots With Power | -47 | 1 | HIGH |
| 10 | Places Shots | -47 | 2 | HIGH |
| 11 | Curls Ball | -47 | 3 | HIGH |
| 12 | Likes To Round Keeper | -47 | 4 | HIGH |
| 13 | Likes To Try To Beat Offside Trap | -47 | 5 | HIGH |
| 14 | Uses Outside Of Foot | -47 | 6 | HIGH |
| 15 | Marks Opponent Tightly | -47 | 7 | HIGH |
| 16 | Winds Up Opponents | -46 | 0 | HIGH |
| 17 | Argues With Officials | -46 | 1 | HIGH |
| 18 | Plays With Back To Goal | -46 | 2 | HIGH |
| 19 | Comes Deep To Get Ball | -46 | 3 | HIGH |
| 20 | Plays One-Twos | -46 | 4 | HIGH |
| 21 | Likes To Lob Keeper | -46 | 5 | HIGH |
| 22 | Dictates Tempo | -46 | 6 | HIGH |
| 23 | Attempts Overhead Kicks | -46 | 7 | HIGH |
| 24 | Looks For Pass Rather Than Attempting To Score | -45 | 0 | HIGH |
| 25 | Plays No Through Balls | -45 | 1 | HIGH |
| 26 | Stops Play | -45 | 2 | HIGH |
| 27 | Knocks Ball Past Opponent | -45 | 3 | HIGH |
| 28 | Moves Ball To Right Foot Before Dribble Attempt | -45 | 4 | HIGH |
| 29 | Moves Ball To Left Foot Before Dribble Attempt | -45 | 5 | HIGH |
| 30 | Dwells On Ball | -45 | 6 | HIGH |
| 31 | Arrives Late In Opponents Area | -45 | 7 | CONFIRMED |
| 32 | Tries To Play Way Out Of Trouble | -44 | 0 | HIGH |
| 33 | Stays Back At All Times | -44 | 1 | HIGH |
| 34 | Avoids Using Weaker Foot | -44 | 2 | HIGH |
| 35 | Tries Tricks | -44 | 3 | HIGH |
| 36 | Tries Long Range Free Kicks | -44 | 4 | HIGH |
| 37 | Dives Into Tackles | -44 | 5 | HIGH |
| 38 | Does Not Dive Into Tackles | -44 | 6 | HIGH |
| 39 | Cuts Inside | -44 | 7 | HIGH |
| 40 | Hugs Line | -43 | 0 | HIGH |
| 41 | Gets Crowd Going | -43 | 1 | HIGH |
| 42 | Tries First Time Shots | -43 | 2 | HIGH |
| 43 | Tries Long Range Passes | -43 | 3 | HIGH |
| 44 | Likes Ball Played Into Feet | -43 | 4 | HIGH |
| 45 | Hits Free Kick With Power | -43 | 5 | HIGH |
| 46 | Likes To Beat Man Repeatedly | -43 | 6 | HIGH |
| 47 | Likes To Switch Ball To Other Flank | -43 | 7 | CONFIRMED |

## Club / Nation

Club usa registros de 440 bytes e Nation de 700 bytes. Em ambos, a assinatura começa em `+0`, o UID público fica em `+20` e o ordinal interno em `+24`. Os namespaces continuam separados. Em RAM foram confirmados, entre outros, Barcelona 1708/411, Sevilla 1759/429, Argentina 1649/187 e Brasil 1651/189. Em Club, Cash foi confirmado em `+248`. Em Nation, Development, Economic Factor e Reputation foram confirmados; League Standard ficou com dois candidatos adjacentes e confiança baixa.

### Club Info

| Índice FMM | Campo | Offset | Tipo | Confiança |
|---|---|---|---|---|
| 0 | Last Division |  |  | UNRESOLVED |
| 1 | Last Position |  |  | UNRESOLVED |
| 2 | Match Day |  |  | UNRESOLVED |
| 3 | Prof. Status |  |  | UNRESOLVED |
| 4 | Reputation |  |  | UNRESOLVED |
| 5 | Facilites |  |  | UNRESOLVED |
| 6 | Youth Setup |  |  | UNRESOLVED |
| 7 | Average Attend |  |  | UNRESOLVED |
| 8 | Minimum Attend |  |  | UNRESOLVED |
| 9 | Maximum Attend |  |  | UNRESOLVED |
| 10 | Cash | 248 | u32 | CONFIRMED |
| 11 | Transfer Budget |  |  | UNRESOLVED |
| 12 | Budget Remain |  |  | UNRESOLVED |
| 13 | Available(%) |  |  | UNRESOLVED |
| 14 | Wage Budget |  |  | UNRESOLVED |
| 15 | Used |  |  | UNRESOLVED |
| 16 | Name |  |  | UNRESOLVED |
| 17 | Capacity |  |  | UNRESOLVED |
| 18 | Seating |  |  | UNRESOLVED |
| 19 | Used Cap. |  |  | UNRESOLVED |
| 20 | Expansion Cap. |  |  | UNRESOLVED |
| 21 | Pitch Width |  |  | UNRESOLVED |
| 22 | Pitch Length |  |  | UNRESOLVED |

### Nation Info

| Índice FMM | Campo | Offset | Tipo | Confiança |
|---|---|---|---|---|
| 0 | Capital |  |  | UNRESOLVED |
| 1 | FIFA Ranking |  |  | UNRESOLVED |
| 2 | Ranking Points |  |  | UNRESOLVED |
| 3 | Stadium |  |  | UNRESOLVED |
| 4 | Group Member |  |  | UNRESOLVED |
| 5 | Importance |  |  | UNRESOLVED |
| 6 | League Standard | [230, 231] | candidate u8 pair | LOW |
| 7 | Development | 228 | u8 | CONFIRMED |
| 8 | Economic Factor | 233 | u8 | CONFIRMED |
| 9 | Reputation | 252 | u16 | CONFIRMED |

## Relação com database

| Campo | RAM | people_db/server_db/client_db | Relação | Confiança |
|---|---|---|---|---|
| Current Ability | Player UID-204 u16 | people_db UID+15 u16 | RUNTIME_MUTATED | HIGH |
| Potential Ability | Player UID-202 u16 | people_db UID+17 u16 | RUNTIME_MUTATED | HIGH |
| Reputações | Player UID-210/-208/-206 u16 | people_db UID+9/+11/+13 u16 | UNKNOWN | MEDIUM |
| Nation | Player UID+64 pointer -> Nation | people_db UID-19 internal id | REFERENCE | HIGH |
| Height/Weight | Player UID-76/-78 u16 | offset de database não resolvido | UNKNOWN | HIGH (RAM) |

## Ranking de matches principais

### Home Reputation = 8198

1. `Player UID-210`, u16, diff manual 8198→8197, score 100, `CONFIRMED`.
2. Demais coincidências fora do objeto Player foram rebaixadas por ausência da assinatura e conflito entre jogadores.

### World Reputation = 5862

1. `Player UID-206`, u16, diff manual 5862→5861, score 100, `CONFIRMED`.

### Height / Weight

1. `UID-76` / `UID-78`, u16, diffs manuais Saviola 168→169 e 61→62; Zidane (185/80) como âncora, score 100, `CONFIRMED`.

### International caps / goals

1. `UID+72` / `UID+74`, u8, Saviola (29/1) e Zidane (95/26), score 100, `HIGH`.

## Evidência de snapshots

- `workspace/live_memory/3100367/saviola_original.json`
- `workspace/live_memory/3100367/saviola_ca161.json`
- `workspace/live_memory/3100367/saviola_ca160_pa178_v2.json`
- `workspace/live_memory/*/baseline_20261012*.json`
- `workspace/live_memory/3100367/fmm_batch_player_baseline.json`
- `workspace/live_memory/3100367/manual_changes_observed_20261012.json`
- `workspace/live_memory/fmm_manual_batch/*/manual_changes_observed_20261012.json`
- `workspace/live_memory/3100367/fmm_batch_remaining_round_20261012_*.json`
- `workspace/live_memory/fmm_manual_batch/*/remaining_round_20261012_*.json`

Os diffs decodificados estão em `manual_change_observations.json`/`.csv` e `remaining_round_analysis.json`/`.csv`. Somente pares atribuíveis sem ambiguidade foram promovidos a `CONFIRMED`.

Os endereços absolutos são deliberadamente omitidos do schema operacional; eles mudam entre processos.
