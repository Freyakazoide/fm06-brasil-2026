# Competições brasileiras (FM06 6.0.2)

## Conclusão principal

**O formato das ligas está no código do `fm.exe`, não no banco.** O banco
guarda o cadastro (ID, nome, reputação). Número de clubes, níveis, acesso e
rebaixamento e datas ficam em classes C++ dentro do executável.

Consequências:

- Mudar números (clubes por série, vagas de acesso e rebaixamento, datas) =
  **patch no `fm.exe`**, trocando constantes.
- Criar a Série D = **acrescentar um 4º nível** no código que monta o sistema
  de ligas do Brasil e dar a ele uma competição. O mais viável é reaproveitar
  uma competição brasileira que já existe e renomeá-la por `.lnc`. Exige um
  patch com código novo (code cave), não só a troca de uma constante.

## IDs (lang_db, nomes em português)

| ID | Nome | Hex |
|---|---|---|
| 102423 | Brasileirão - Primeira Divisão | 0x19017 |
| 107191 | Brasileirão - Segunda Divisão | 0x1A2B7 |
| 107192 | Brasileirão - Terceira Divisão | 0x1A2B8 |

O registro de nome no `lang_db` é: u32 ID, nome longo (u32 tamanho + UTF-16),
nome curto, 1 byte, abreviação (ex.: `1D`, `2DN`, `3DN`).

## server_db: tabela de competições

- Em `0x005B85C0`: 1.079 registros de 52 bytes, cada um com u32 índice
  (0..1078) e u32 ID da competição.
- Os campos restantes ainda não foram decodificados. Não contêm o formato da
  liga.
- Atenção: um mesmo número pode ser ID de competição e de prêmio no
  `lang_db`. Para achar o nome, buscar só na tabela de nomes de competição.

## fm.exe: módulo Brasil (`0x00BB2700`–`0x00BC0000`)

Os IDs 0x19017, 0x1A2B7 e 0x1A2B8 aparecem como constantes só nessa faixa.

### Sistema de ligas do Brasil (`0x00BB2710`)

```
new objeto (0x58 bytes)
init(2)
[esi+0x18] = 0x14 (20)
adicionar_divisão(0x19017, nível 0)   ; Primeira
adicionar_divisão(0x1A2B7, nível 1)   ; Segunda
adicionar_divisão(0x1A2B8, nível 2)   ; Terceira
[esi+0x0A] = 1 ; [esi+0x09] = 1
finalizar(3)                          ; 3 níveis?
```

`adicionar_divisão` = `0x00AD0050(id, nível, 0)`. Para a Série D, seria
preciso uma 4ª chamada com nível 3, e provavelmente trocar `finalizar(3)`
por 4.

### Classe da Série A (construtor em `0x00BB2CC0`)

- Vtables: `0x0113B2FC`, `0x0113B2E8`, `0x0113B2C0`, `0x0113B2B4` e
  `0x0113B2A0`.
- Campos fixados no construtor: `+0x80`=1, `+0x85`=3, `+0x87`=0x0B.
- Métodos próprios da Série A na vtable principal:
  - [63] `0x00BB2D60` devolve 15000;
  - [69] `0x00BBA3F0`;
  - [71] `0x00BBA400`, provável montagem das fases;
  - [74] `0x00BB2D90`;
  - [76] `0x00BB2D70`.
- O método [71] usa as constantes 20 (`0x14`), 26 (`0x1A`), 30 (`0x1E`),
  16 (`0x10`) e várias datas (dia, mês). Também referencia a Segunda Divisão
  (`push 2 ; push 0x1A2B7`), provavelmente o rebaixamento.

## Funções exportadas por país

O `fm.exe` exporta 363 funções com nome. Cada país tem o mesmo conjunto,
com o prefixo do país (`bra_`, `eng_`, `arg_`…):

| Função | Endereço (Brasil) | Papel |
|---|---|---|
| `bra_get_settings` | 0x00BB2710 | sistema de ligas: Primeira no nível 0, Segunda no 1, Terceira no 2 |
| `bra_setup_comps` | 0x00BBA2C0 | cria as 5 competições (Série A `0xBB2CC0`, B `0xBB2DF0`, C `0xBB2EC0`, `0xBB96E0`, `0xBB30F0`) |
| `bra_get_minimum_division_teams` | 0x00BB2840 | mínimo de clubes: Série A 20, B 20, C 128, mais estaduais |
| `bra_setup_fixture_rules` | 0x00BBA3B0 | calendário |
| `bra_setup_discipline_rules` | 0x00BB2800 | cartões e suspensões |
| `bra_setup_transfer_rules` | 0x00BBAD10 | janelas de transferência |

## Montagem das fases (método 71 de cada classe)

| Série | Método | Clubes | Acesso | Rebaixamento |
|---|---|---|---|---|
| A | `0x00BBA400` | 20 (`*param_3 = 0x14`) | — | 2 para a B: `FUN_00b0feb0(0x1A2B7, 2, -1)` |
| B | `0x00BBA6A0` | 20 | 2 para a A: `FUN_00b0fe50(0x19017, 2, -1)` | 2 para a C: `FUN_00b0feb0(0x1A2B8, 2, -1)` |
| C | `0x00BBFD00` | 128 em fases | 2 para a B | `FUN_00b0feb0(0x13DBB8, 2, -1)` |

API das fases (deduzida comparando com a Championship inglesa, que tem 3
acessos e 3 rebaixamentos e no código aparece como `(…, 3, -1)`):

| Função | Significado |
|---|---|
| `FUN_00b164a0(2000, comp, fase)` | cria a fase |
| `fase+0x0B` | clubes por grupo |
| `fase+0x14` | turnos (2 = ida e volta) |
| `fase+0x15` | 3 = pontos por vitória (provável) |
| `FUN_00b0fe50(destino, n, -1)` | **sobem n** clubes para `destino` |
| `FUN_00b0feb0(destino, n, -1)` | **descem n** clubes para `destino` |
| `FUN_00b08360(tipo, dia, mês, 2000)` / `FUN_00b08470(...)` | início e fim (datas; o ano 2000 é base relativa) |
| `FUN_00b08d90(...)` | vagas para outras competições (a decodificar) |
| `FUN_00b0ee30(...)` | registra a fase |

## Patches (`scripts/patch_exe.py`)

Os patches são aplicados numa cópia (`fm_teste.exe`), conferindo o hash do
original e os bytes antes da troca.

| Nome | Troca |
|---|---|
| `serie_a_rebaixa_4` | arquivo 0x7BA4F3: `6A 02 68 B7A20100` → `6A 04 …` |
| `serie_b_sobe_4` | arquivo 0x7BA795: `6A 02 68 17900100` → `6A 04 …` |
| `serie_b_rebaixa_4` | arquivo 0x7BA7A8: `6A 02 68 B8A20100` → `6A 04 …` |

## Próximos passos

1. Decodificar os métodos [71] da Série A e os equivalentes da B e da C:
   número de clubes, turnos, acesso e rebaixamento, datas.
2. Primeiro teste de patch numa **cópia** do `fm.exe`: trocar uma constante
   simples (por exemplo, a quantidade de rebaixados) e confirmar no jogo.
3. Planejar o 4º nível (Série D) com code cave.
