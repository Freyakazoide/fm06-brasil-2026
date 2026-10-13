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
- Na cópia: sem final (vencedores da semifinal sobem), sorteio 13/11, 1º jogo
  21/11, 2º jogo uma semana depois.
- A fase de pontos corridos da Série B termina em 8/11 (`serie_b_datas_2026`).

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

## Teste 1 de `serie_b_playoffs`

- ✅ Regras: "Equipas classificadas entre 3-6 qualificam-se para o Playoff";
  na classificação, 3º a 6º marcados "Pl".
- ✅ Calendário: "Playoff - Meia Final" ida 19/11 e volta 22/11.
- ❌ Os jogos do playoff não aconteceram, e em 31/1/2007 o Brasil estava sem
  calendário novo, sem acesso e rebaixamento e sem estaduais.
- Causa provável: a 38ª rodada caiu em 18/11 (o jogo arredonda o fim da fase
  para o fim de semana) e o sorteio do playoff era em 16/11, antes do fim da
  liga. O playoff ficou sem times, a Série B nunca terminou, e o jogo não
  fecha a temporada do país enquanto uma divisão não termina.
- Correção: fim da fase de liga em 8/11 e sorteio em 13/11. Regra geral:
  deixar pelo menos uma semana entre o fim de uma fase e o início da seguinte.

## Teste 3: a fase seguinte não é gerada em nenhuma série

- C: 1ª fase 8/4–26/8 (o jogo arredonda o fim para o sábado), fase de
  grupos marcada no "Programa" de 3/9 a 29/10, mas sem jogos. B e D: igual.
- O "Programa" mostra fases futuras com fases temporárias (`0x00ACEC70`,
  `0x00ACAC30` chamam o método 71 só para calcular datas). Ou seja, a fase
  aparecer no calendário não quer dizer que ela foi criada.
- Competição: `+0x100` = número de fases (gravado por `0x00AC24F0`), `+0x90`
  = ARRAY das fases criadas (itens em `+0x94`, quantidade em `+0x98`). Só
  termina quando `+0x98` chega a `+0x100` (`0x00AC6131`).
- `0x00AC70C0` acrescenta uma fase à competição (chamado pelos módulos de
  cada país).
- A ação de qualificação (`LEAGUE_FATE_ACTION_QUALIFICATION`, vtable
  `0x011178B8`, criada por `0x00B0FF00`) guarda a zona em `+8` e um
  `NEXT_STAGE_INFO` (vtable `0x01117604`) com o código da próxima fase em
  `+0x14`.
- Sondagem na memória: `scripts/probe_stages.py`.

## Causa: ninguém criava a fase seguinte (método 72)

Sondagem no save travado (`probe_stages.py`): A 1/1 fases, B 1/2, C 1/2, D 1/3.

- O motor (`0x00AC5BD9`) percorre as fases criadas e, quando uma termina,
  chama o **método 72** da competição (vtable `+0x120`), passando a fase.
- Cada liga implementa o próprio método 72; o padrão (`0x007560A0`) não faz
  nada. A e B usavam o padrão. A antiga C tem `0x00BBA900`: fase 0 terminou →
  `0x00BB90D0` (mata-mata com os 32 do código 7); fase 1 → `0x00BB5B60`
  (fase final com os do código 0xA7).
- Criar uma fase: lista de times (vtable `0x00EB4ECC`), classificados da fase
  anterior pelo código (`NEXT_STAGE_INFO`; liga: `0x00B18D50`, grupos:
  `0x00B577B0`, mata-mata: `0x00B3E6E0`), fase nova (liga `0x00B16BC0`,
  grupos `0x00B5ADC0`, mata-mata `0x00B44060`) e `0x00AC5150` (acrescenta).
- Championship: método 72 `0x00C13C80` → `0x00C122F0` (código 0x15). Série B
  italiana: `0x00C0CB60` → `0x00C0A810` (código 0x75; se não vierem 4 times,
  acrescenta uma fase vazia).

Correção:
- Série B: zona de playoff com o código 0x75 e método 72 próprio
  (`0x015B4C00`) que chama `0x00C0A810`, a criação do playoff italiano (o
  mesmo conjunto da cópia da montagem italiana).
- Nova C: método 72 próprio (`0x015B4B00`): fase 0 terminou → classificados
  com o código 0x49 → `GROUP_STAGE(1, lista, 0)` → acrescenta.
- Série D: a antiga C já tinha o método 72, mas os jogos dos grupos foram até
  1/8 com o mata-mata marcado para 26/7. Datas com mais folga: grupos até 9/8,
  mata-mata 16/8, fase final 16/9 a 28/10.

## Teste 4: crash em 21/08/2006

Dump: acesso a endereço nulo em `0x00B07E4A`, comparador do `qsort`
(`0x00D7E7C0`) chamado por `0x00B0D8CC` para ordenar a tabela (linhas de
0x4C bytes): uma linha sem time. Suspeita: a fase de grupos da nova C foi
criada com a lista de classificados vazia. A 1ª fase marcava os 8 com zona 1
+ ação 5 (padrão de fase de grupos); numa fase de liga o coletor
(`0x00B18D50`) usa zona 2 + ação 2 (Championship, Série B italiana).

Correção: nova C com zona 1 = 0 e zona 2 = 8 (ação 2, código 0x49); o método
72 confere se vieram exatamente 8 times e, se não vierem, fecha a fase com
uma fase vazia (como a Série B italiana faz), em vez de criar grupos com
vagas vazias.

## Teste 5: ✅ as fases são criadas e a temporada vira

Sondagem (`probe_stages.py`) em um jogo novo:

| Data | A | B | C | D |
|---|---|---|---|---|
| 15/08/2006 | 1/1 | 1/2 | 1/2 | 1/3 |
| 01/09/2006 | 1/1 | 1/2 | **2/2** (GROUP_STAGE, 8 times) | 1/3 |
| 25/11/2006 | 1/1 | **2/2** (CUP_STAGE, playoff) | 2/2 | **3/3** (mata-mata e fase final) |
| 2007 | 1/1 | 1/2 | 1/2 | 1/3 (ano `+0x9C` = 2007: temporada nova criada) |

Pendente: na Série D, a 10ª rodada dos grupos ficou para 20/9, depois do
início do mata-mata (20/8): a fase só terminou em setembro e o mata-mata foi
criado atrasado. Precisa de mais folga ou de menos conflito com os estaduais.
