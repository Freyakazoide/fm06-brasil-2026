# Estaduais no fm.exe

## Quem cria

`BRA_STATE` (ID 0x23D8D, construtor `0x00BB96E0`) é o contêiner "Brazilian
State Championships". Ele cria um objeto por estado, escolhendo a classe:

| Construtor | Classe | Estados (ID) |
|---|---|---|
| `0x00BB50B0` | `BRA_STATE_LEAGUE` (genérico, parametrizado) | SP 0x1901A, AC 0x1A2B2, AM 0x49C7F, GO 0x4B9B0, MG 0x4B9B2, AP 0x4C768, DF 0x4C76C, ES 0x4C76E, MS 0x4C772, MT 0x4C774, PI 0x4C778, RN 0x4C77A, RO 0x4C77C, RR 0x4C77E, SE 0x4C780, TO 0x4C782 |
| `0x00BB5310` | `BRA_STATE_PARAIBA` | AL 0x1A2B1, AM 0x49C7F, PE 0x4B9B4, CE 0x4C76A, MA 0x4C770, PB 0x4C776 |
| `0x00BB5390` | `BRA_STATE_PARANA` | PR 0x4B9B6 |
| `0x00BB5410` | `BRA_STATE_PERNAM` | PE 0x4B9B4 |
| `0x00BB5510` | `BRA_STATE_TOCAN` | TO 0x4C782 |
| `0x00BB5610` | `BRA_STATE_GAUCHO` | RS 0x49C7D |
| `0x00BB5690` | `BRA_STATE_BAHIA` | BA 0x4B9AE |
| `0x00BB5720` | `BRA_STATE_RIO` | RJ 0x19018 |
| `0x00BB7350` | `BRA_STATE_SANTA` | SC 0x4B9B8 |
| `0x00BB7870` | `BRA_STATE_PARA` | PA 0x4C784 |

AM, PE e TO aparecem com duas classes: o contêiner escolhe pelo argumento do
construtor (provável nível de detalhe do banco carregado).

Nomes: `lang_db.dat`, registros `u32 ID | u32 tamanho | nome UTF-16 | 00 |
nome curto | 00 | sigla`.

## Parâmetros do estadual genérico

`0x00BB3330` (chamado no construtor, `this` = competição + 0x1A4) preenche um
bloco por estado:

| Campo (competição +) | Uso no montador `0x00BBB100` |
|---|---|
| `0x1A4` | ID do estadual |
| `0x1A8` | número de clubes |
| `0x1A9` | grupos (1 = liga única; > 1 = fase de grupos, clubes / grupos por grupo) |
| `0x1AA` | turnos (1, 2 ou 3) |
| `0x1AB` | quantos avançam para o mata-mata (zona 1 com ação 5 → fase de código 0x15); 0 = o 1º é campeão |
| `0x1AC` | quantos caem |
| `0x1B0`, `0x1B4` | prêmios |
| `0x1B8` | ID da divisão de baixo (destino do rebaixamento) |
| `0x1BC`… | 2ª fase (liga final se `0x1BC` = 1, com turnos em `0x1C0`; senão mata-mata, ida e volta em `0x1BE`) |

Datas: `0x00BB3DF0` (início 16/1; fim conforme o estado ou calculado pelo
número de rodadas). Exemplos da tabela original:

| UF | Clubes | Grupos | Turnos | Avançam | Caem |
|---|---|---|---|---|---|
| SP | 20 | 1 | 1 | 0 | 4 |
| RJ | 12 | 2 | 1 | 4 | 1 |
| RS | 18 | 2 | 1 | 4 | 2 |
| BA | 13 | 1 | 1 | 8 | 2 |
| CE | 10 | 1 | 1 | 2 | 2 |
| AC | 6 | 1 | 3 | 0 | 1 |
| AL | 10 | 1 | 2 | 0 | 1 |
| AM | 8 | 1 | 1 | 2 | 1 |
| AP | 8 | 1 | 2 | 0 | 1 |

Tabela original completa (emulação de `0x00BB3330` para os 27 IDs; os
estados de classe própria também têm entrada):

| UF | Clubes | Grupos | Turnos | Avançam | Caem | 2ª fase (+0x18) | Divisão de baixo |
|---|---|---|---|---|---|---|---|
| AC | 6 | 1 | 3 | 0 | 1 | 7 | 0x1A2B4 |
| AL | 10 | 1 | 2 | 0 | 1 | 7 | 0x1A2B3 |
| AM | 8 | 1 | 1 | 2 | 1 | 0 | 0x49C80 |
| AP | 8 | 1 | 2 | 0 | 1 | 7 | 0x4C769 |
| BA | 13 | 1 | 1 | 8 | 2 | 0 | 0x4B9AF |
| CE | 10 | 1 | 1 | 2 | 2 | 0 | 0x4C76B |
| DF | 12 | 2 | 2 | 4 | 2 | 1 | 0x4C76D |
| ES | 10 | 1 | 2 | 0 | 2 | 7 | 0x4C76F |
| GO | 12 | 1 | 1 | 8 | 3 | 0 | 0x4B9B1 |
| MA | 8 | 1 | 1 | 2 | 2 | 0 | 0x4C771 |
| MG | 12 | 1 | 1 | 4 | 2 | 0 | 0x4B9B3 |
| MS | 8 | 1 | 2 | 0 | 2 | 7 | 0x4C773 |
| MT | 14 | 1 | 1 | 0 | 3 | 7 | 0x4C775 |
| PA | 10 | 1 | 1 | 2 | 2 | 0 | 0x4C785 |
| PB | 10 | 1 | 2 | 2 | 1 | 0 | 0x4C777 |
| PE | 10 | 1 | 1 | 2 | 2 | 1 | 0x4B9B5 |
| PI | 8 | 1 | 2 | 0 | 2 | 7 | 0x4C779 |
| PR | 16 | 2 | 1 | 4 | 2 | 0 | 0x4B9B7 |
| RJ | 12 | 2 | 1 | 4 | 1 | 0 | 0x4CD6B |
| RN | 14 | 1 | 1 | 8 | 2 | 0 | 0x4C77B |
| RO | 8 | 1 | 2 | 0 | 2 | 7 | 0x4C77D |
| RR | 8 | 1 | 2 | 0 | 1 | 7 | 0x4C77F |
| RS | 18 | 2 | 1 | 4 | 2 | 0 | 0x49C7E |
| SC | 12 | 2 | 2 | 4 | 1 | 0 | 0x4B9B9 |
| SE | 10 | 1 | 2 | 0 | 2 | 7 | 0x4C781 |
| SP | 20 | 1 | 1 | 0 | 4 | 7 | 0x4CD6C |
| TO | 10 | 1 | 2 | 0 | 1 | 7 | 0x4C783 |

2ª fase (+0x18): 0 = mata-mata, 1 = liga final, 7 = nenhuma.

## Mata-mata do genérico

Com +0x18 = 0, a 2ª fase é um mata-mata dos `0x1AB` classificados: 8 →
quartas (rodada 0x11), semifinal (0x12) e final (0x14); 4 → semifinal e
final; 2 → final. As datas derivam do fim da fase de liga (`0x00BB3DF0`):
quartas `0x00BB4200` = fim + 1 semana; semifinal `0x00BB42B0` = quartas + 1
(ou fim + 1); final `0x00BB4370` = semifinal + 2 (ou fim + 1).

## Patch `estaduais_2026`

`src/fm06patch/estaduais.py`: todos os estados no genérico (14 chamadas de
construtor trocadas no contêiner), formato de 2026 gravado depois da tabela
original e fase de liga de 11/1 até 8/2 (8 classificados), 15/2 (4), 1/3 (2)
ou 8/3 (nenhum), para a final cair em 8/3. Emulação conferida para SP, RJ,
PR, AC e MS.

Teste no jogo (New Game 2006): Carioca em 2 grupos; Baiano, Acreano,
Catarinense, Pernambucano, Cearense, Alagoano, Maranhense, Mato-Grossense e
Goiano gerados. Paulista (16), Gaúcho (12) e Paranaense (12) sem os grandes:
com menos vagas que clubes no estado, o jogo usa os primeiros da lista. Esses
voltaram ao número original (20, 18, 16), assim como RN, TO, DF e RO.

Virada 2006 → 2007 (probe em 16/1/2007): séries e Copa do Brasil em 2007,
mas o contêiner dos estaduais ficou em 2006 e nenhum estadual de 2007 foi
criado. Baiano, Mato-Grossense e Paraense com 1/2 fases: a fase de liga
(10 clubes, 9 rodadas, 11/1 a 15/2) não terminou a tempo e o mata-mata não
nasceu. Início em 7/1 não resolveu: no jogo o Baiano tinha 13 clubes na
tabela, o Paraense e o Mato-Grossense 14, com calendário de 10 (9 rodadas;
times com 10 ou 11 jogos de 12 ou 13). O número de clubes do formato tem de
ser o do banco: BA 13, PA 14, MT 14 (a tabela original dizia PA 10, mas o
Paraense tinha classe própria). Com 13 e 14 clubes o teste seguinte
mostrou a causa real: o jogo só marca as rodadas que cabem até o fim da
fase de liga (domingo e quarta). Com fim em 15/2, o Baiano (13 rodadas)
teve só 11 marcadas, de 8/1 a 12/2, e as outras 2 nunca aconteceram. Agora o
fim é por estado (bytes 10 e 11 da entrada da tabela): o fim do formato
(8/2, 15/2, 1/3 ou 8/3) ou, se as rodadas não cabem, 7 dias depois da
última (BA, PA e MT: 26/2).

Isso cobre direto os modelos M1 e M3 de `docs/REGRAS_2026_ESTADUAIS_E_COPAS.md`
(liga única + mata-mata de 4 ou 8). Para os demais modelos falta ver o que o
mata-mata do genérico suporta (6 classificados, 1º e 2º direto à semi) e se
os grupos podem jogar contra o outro grupo.

## Participantes (banco) e vagas

- Quem joga cada estadual: `0x00BB6290` → `0x00AC6F70(ID do estadual, lista)`
  junta **todos** os times com `TEAM+0x64` = aquela competição; o número de
  clubes dos parâmetros só serve para o calendário. No `server_db.dat` o
  campo fica no registro do time, 47 bytes depois do `0A 00`: índice da 1ª
  ou da 2ª divisão do estado na tabela de competições (ex.: BA 324 e 325,
  SP 75 e 374). Os 671 clubes brasileiros têm um dos 54 índices.
- `src/fm06patch/estaduais_clubes.py` grava a lista de 2026
  (`data/brasil/estaduais/clubes_2026_modelo.csv`): quem está na lista vai
  para a 1ª divisão do estado, quem estava e não está vai para a 2ª; clube
  que não existe no FM06 é trocado pelo de maior reputação do estado (93 de
  268; mapa em `data/brasil/estaduais/mapa_estaduais_2026.csv`). O número de
  clubes do formato sai da mesma lista (`estaduais.club_counts`).
- Vagas: `0x00BB6860` (Copa do Brasil) pega, do estadual ordenado
  (`0x00A1D020`), os N primeiros que ainda não estão na lista, com N =
  competição+0x1C1 (bloco de parâmetros +0x1D; original soma 64, ex.: SP 6,
  RJ 6, MG 4, RS 4, PR 4, PE 3). +0x1C (1 ou 2) é provavelmente a vaga para a
  divisão nacional de baixo (a confirmar).
- `bra_get_minimum_division_teams` (`0x00BB2840`) registra para cada estadual
  um número **exato** de clubes (mínimo = máximo). Com a lista de 2026 a
  contagem mudou e o Brasil sumiu da lista de países do New Game; o patch
  `estaduais_2026` grava agora o número da lista. O leitor por cabeçalho de
  clube (`server_teams.find_brazil_teams`) perdia 53 times de estadual;
  `estaduais_clubes.state_teams` varre o banco inteiro (724 times, as
  contagens batem com as registradas no exe original). As 2ª divisões
  estaduais têm mínimo registrado (3 ou 4, sem máximo); completar as listas
  tira clubes delas (Acre 4 -> 2, Roraima 1 -> 0), então o mínimo delas vai a 0.
