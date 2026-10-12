# people_db.dat (FM06 6.0.2)

Estrutura observada no arquivo de 98.175.429 bytes
(SHA-256 `B21DDF34…5DF4A`, já com o teste de CA do Saviola aplicado).

O jogo lê o arquivo inteiro, em sequência, a cada New Game (Process Monitor).
Os 9 primeiros bytes são lidos separadamente.

## Cabeçalho

| Offset | Tipo | Valor | Interpretação |
|---|---|---|---|
| 0x00 | 2 bytes | `02 01` | versão? |
| 0x02 | 4 bytes | `tad.` | assinatura (".dat" invertido) |
| 0x06 | 3 bytes | `27 01 00` | ? |
| 0x09 | u32 | 277936 | total da tabela A (pessoas, registros de tamanho variável) |
| 0x0D | u32 | 277340 | total da tabela T2 |
| 0x11 | u32 | 222888 | total da tabela T3 |
| 0x15 | u32 | 56704 | total de outra tabela, ainda não localizada |
| 0x19 | u32 | 144090 | total de outra tabela, ainda não localizada |

## Tabelas localizadas

| Tabela | Início | Fim | Registro | Formato |
|---|---|---|---|---|
| A (pessoas) | ~0x1D | ? | variável | registro "core" com UID; strings UTF-16 com nomes |
| T2 | 0x043902BA | 0x0480F3D6 | 17 bytes | u32 índice, u32 UID, 9 bytes |
| T3 | 0x0480F422 | 0x05AFA48A | 89 bytes | u32 índice, u32 UID, 81 bytes com valores 0–20 |

Nas duas tabelas, o índice vai de 0 até total−1, sem buracos.

## O UID do Saviola (3100367) aparece em

| Offset | Tabela | Conteúdo |
|---|---|---|
| 0x03B71E4E | A | `+9/+11/+13` u16 (150/150/125), `+15` u16 = 160 (CA?), `+17` u16 = 180 |
| 0x045CB66F | T2 | `00 0e 0f 10 0c 0d 0e 10 0c` |
| 0x0516EA17 | T3 | 81 bytes, muitos zeros e o resto entre 1 e 20 |

## Testes e conclusões

- Alterar `A+15` de 160 para 111 **não mudou o CA no jogo**, mesmo com o
  jogo lendo o arquivo inteiro. Ou o CA vem de outro lugar, ou é recalculado.
  O comando `WEIGHTING` (posição, atributo, peso) aponta para recálculo.
- No `A+15`, o CA da RAM bateu com o arquivo em 3 de 4 âncoras. O PA (`A+17`)
  nunca bateu: −1, +7, +12 e +7.
- O conteúdo de T2 **não** corresponde à personalidade (PData) lida na RAM.
- O conteúdo de T3 **não** corresponde aos bytes "Playing" lidos na RAM, nem
  diretamente, nem em escala ×5, nem por fórmula linear módulo 256.
  T3 tem exatamente a quantidade de jogadores, então continua sendo a melhor
  candidata a tabela de atributos. Os zeros podem significar "não definido,
  o jogo gera no New Game".

## Próximo passo

Comparar T3 com os atributos 1–20 que o próprio jogo mostra na ficha do
jogador, em vez de comparar com os bytes crus da RAM.
