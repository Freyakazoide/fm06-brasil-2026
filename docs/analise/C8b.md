# Ficha C8b — Regras de transferência do Brasil (argumentos)

- Quem analisou / data: Claude, 2026-11-01
- Ferramenta: Capstone + pefile (`workspace/rea/tools/pe.py`), `fm.exe` 6.0.2 original
- Ponto de partida: ficha C8, `0x00BB32A0` (método 0 de `BRA_TRANSFER_RULES`, vtable
  `0x0113DBF8`)

Método: as 55 chamadas de `0x00ADEDC0`, as 107 de `0x00ADED50` e as 54 de `0x00ADC540`
foram listadas com os `push` e com o nome da classe pelo RTTI (`.?AVENG_TRANSFER_RULES@@`
etc.), e comparadas com as regras conhecidas de cada país.

## Conferido no código

### Datas: formato

(dia da semana, dia, mês, ano), com **1 = domingo** e **mês começando em 0**. Conferido
pelo dia da semana: Inglaterra 13/05/2001 = domingo (1) e 11/08/2000 = sexta (6); Brasil
25/12/2000 = segunda (2) e 15/01/2000 = sábado (7). O dia da semana 0 aparece quando a data
não depende dele.

### `0x00ADEDC0` (8 argumentos): fim e início da temporada de referência

Duas datas. Brasil `(2, 25, 11, 2000)` e `(7, 15, 0, 2000)` = 25/12 e 15/1; Chile 17/12 e
30/1; Argentina 23/7/2001 e 6/8/2000; Inglaterra 13/5/2001 e 11/8/2000; Espanha 1/6/2001 e
25/8/2001. Hipótese: fim e início da temporada usados pelas regras (contratos, prazos). Não
mexido.

### `0x00ADED50` (13 argumentos, `ret 0x34`): janela de transferências

`(dia da semana, dia, mês, ano)` de abertura, `(dia da semana, dia, mês, ano)` de
fechamento, tipo, divisão de, divisão até, 1, 1. Os 5 últimos vão para +0x20…+0x24 do
objeto da janela (`0x00ADED91`…`0x00ADEDB0`); a janela é criada por `0x00ADE280`.

| País | Janelas |
|---|---|
| Inglaterra | 1/7–31/8 e 1/1–31/1, divisões 0 a 4 |
| Espanha, Alemanha, Itália, Portugal, França | 1/7–31/8 e 1/1–31/1, todas (-1) |
| Japão | três janelas, uma com tipo/divisão 1 |
| **Brasil** | **uma só: 1/1–26/9**, todas as divisões (`0x00BB32CD`…`0x00BB32EF`) |

### `0x00ADC540` (3 argumentos, `ret 0xC`): regra numérica

`(tipo, valor, competição)`: grava um nó de 12 bytes (+4 tipo, +5 valor, +8 competição
resolvida por `0x00582440`, -1 = todas) na lista `[regras+0x10]`; tipo 5 também liga
`[regras+0x4E]` (`0x00ADC581`). Brasil: tipo 4 = 3 e tipo 5 = 0. Tipo 4 aparece em Chile
(4), Japão (5), EUA (7); tipo 3 em França (4/4/2 por divisão), Portugal e Alemanha (com UID
de competição); tipo 6 na Itália (1, Séries A e B; hipótese: contratações de fora da UE por
temporada). O significado do tipo 4 não foi provado.

### `0x00AD98B0` (4 argumentos)

Brasil, Colômbia e Portugal `(8160, 1, -1, -1)`; Inglaterra 8191; Espanha, Alemanha,
Itália e França 4096. Parece máscara de bits. Não identificado.

### Limite de estrangeiros por jogo: outro sistema

O texto "Maximum of <%number#1> Foreign Players" (`0x010F3290`) é escrito por `0x00A57460`
para as regras de **inscrição da competição** (códigos 2, 3, 4, 0x15, 0x34 e 0x35 =
estrangeiros; 5, 6, 7 e 0x12 = fora da UE), chamado de `0x00870738` com a lista
`[[x+0x64]+0x14]` (quantidade em +0x1C). Não é o `BRA_TRANSFER_RULES`. Falta achar onde
as competições brasileiras gravam essa regra (no código ou no `server_db`).

## Dados de 2026 (fontes)

- Janelas da CBF em 2026: 5/1 a 3/3 e 20/7 a 11/9; janela complementar de 4 a 27/3 só para
  quem jogou estadual ou rescindiu na 1ª janela.
  [Itatiaia](https://www.itatiaia.com.br/esportes/futebol/futebol-nacional/veja-todas-as-datas-do-novo-calendario-do-futebol-brasileiro-em-2026/),
  [Descomplica](https://descomplica.com.br/blog/janela-extra-ate-27-3-quem-vai-chegar-no-seu-time-2/),
  [Band](https://www.band.com.br/esportes/janela-internacional-de-transferencias-abre-hoje-veja-detalhes-202607191440)
  (uma matéria da 90min fala em 17/7 para a 2ª; as outras, 20/7).
- Estrangeiros relacionados por jogo nas Séries A e B: 9 em 2026; aprovado em 21/09/2026
  cair para 8 (2027), 7 (2028), 6 (2029) e 5 (2030).
  [SBT News](https://sbtnews.sbt.com.br/noticia/brasil/cbf-aprova-reducao-gradual-de-estrangeiros-no-brasileirao),
  [Times Brasil](https://timesbrasil.com.br/esportes/cbf-e-clubes-aprovam-reducao-do-limite-de-estrangeiros-a-partir-de-2027/).

## Consequência

- Patch `janelas_2026` (`src/fm06patch/transferencias.py`): a 1ª janela troca os `push`
  no lugar (dia de abertura 1 -> 5 em `0x00BB32E9`; fechamento 26/9 -> 3/3 em
  `0x00BB32DE`/`0x00BB32DC`); a 2ª (20/7 a 11/9) entra por um stub na .fm26+0x6240,
  chamado de `0x00BB32F4` no lugar de `push -1 ; push 3 ; push 4 ; mov ecx, esi ; call
  0x00ADC540` (13 bytes: `call` + 8 `nop`), que grava a janela e refaz essa chamada. A
  janela complementar de março fica de fora (o jogo não tem a restrição de quem jogou
  estadual).
- Limite de 9 estrangeiros: depende de achar a regra de inscrição (acima).

## Diário

- 01/11, patch `janelas_2026` escrito. Testes: a janela original desmontada é 1/1–26/9; com
  o patch, 5/1–3/3 no lugar e o stub com 20/7–11/9 seguido da chamada original; aplica com
  todos os outros patches.
- 01/11, instalado (`aplicar_tudo --rapido`): no `fm_brasil.exe` a 1ª janela tem `push 5`
  (0x00BB32E9), `push 3`/`push 2` (0x00BB32DE/0x00BB32DC), `0x00BB32F4` = `call
  0x015BA240` + 8 `nop`, e o stub com 20/7 (`push 0x14`, `push 6`) a 11/9 (`push 0xB`, `push
  8`) seguido de `push -1 ; push 3 ; push 4 ; call 0x00ADC540 ; ret`. Falta ver no jogo.
- 01/11, busca do limite de estrangeiros (em andamento): `0x00A57460` (texto das regras de
  inscrição) não é virtual e só é chamado de `0x00870738` (tela). Classes com RTTI por
  perto: `RULE_GROUP_ARRAY` (vtable `0x00EA4B78`, construtor `0x004C6DF0`, chamado só de
  `0x00E0FE40`) e `LEAGUE_SETTINGS` (`0x011180AC`, as regras da fase de liga da C9b). Hipótese:
  as regras de inscrição vêm do `server_db` (dados da competição), não do código. Próximo:
  ver no jogo o que a Série A mostra hoje e procurar o registro no banco.

