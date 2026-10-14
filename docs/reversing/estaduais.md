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

Isso cobre direto os modelos M1 e M3 de `docs/REGRAS_2026_ESTADUAIS_E_COPAS.md`
(liga única + mata-mata de 4 ou 8). Para os demais modelos falta ver o que o
mata-mata do genérico suporta (6 classificados, 1º e 2º direto à semi) e se
os grupos podem jogar contra o outro grupo.
