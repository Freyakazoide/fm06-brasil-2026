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

## Teste: padrão na T3 do Saviola

Gravamos `(j % 20) + 1` nos 81 bytes do registro T3 do Saviola (`0x0516EA13`).
O New Game **crashou**:

- Erro de acesso a memória em `fm.exe` `0x009F02C5`, ao ler o endereço 0.
- O código percorria uma coleção e chamou um método virtual num elemento
  nulo (índice 0).

Conclusão: a T3 não guarda só valores de 0 a 20. Pelo menos algumas colunas
são referências ou flags, e o padrão criou referências inválidas. Testes
futuros na T3 devem alterar uma coluna por vez, mantendo valores plausíveis.

## Atributos na memória (validado com as fichas do Saviola e do Zidane)

- **Absolutos** (físicos e parte dos mentais: Velocidade, Força, Determinação,
  Instinto, Agressividade…): memória = 5 × valor exibido (+0 ou +1).
- **Relativos ao CA** (técnicos e parte dos mentais: Finalização, Passe,
  Decisões, Posicionamento, Compostura…): byte com sinal; o valor exibido é
  `(memória + base) / 5`, arredondado para baixo e limitado a 20. A base
  depende do CA: 86 com CA 160 (Saviola), 97 com CA 185 (Zidane).
- As posições ficam direto na escala 1–20.

## Registro da pessoa e staff (técnico, comissão)

Ordem no arquivo (`src/fm06patch/comissao.py`):

- u32 primeiro nome, u32 sobrenome, u32 nome comum (índices das tabelas de nomes
  do server_db: primeiro 0x5C0000–0x85D000, sobrenome –0xDE5A60, comum –0xEE7000;
  cada nome é u32 tamanho, UTF-16, 00 00, u16 uso, u32 nação, u32 índice, u32
  UID, 00), u32 tamanho + nome completo (+ 00 00 se houver);
- u16 dia do ano e u16 ano do nascimento, 00, u32 nação (0xBD Brasil), u32
  seleção, u32 jogos, u32, 00, data, **u32 time** (índice do time − 1), **u8
  cargo**, data de chegada, u32...;
- contrato: 64, u32 pessoa, 00, u32 índice do clube, u32 salário, u16 dia e u16
  ano do fim (0 / 1900 = sem data), 02 00 00 00 (é o mesmo bloco dos jogadores;
  a busca antiga só achava fins de contrato de 2005 a 2014);
- u32 pessoa, u32 UID (o do `CHANGE_PLAYER_NAME`).

Cargo: 16 técnico, 20 auxiliar, 2 treinador, 12 fisioterapeuta/médico, 14
olheiro, 1 jogador; 4, 8 e 10 aparecem em poucos clubes (diretoria). Nação: a
Europa (0x81…) e a CONMEBOL (0xBB Argentina … 0xC4 Venezuela) seguem a ordem
alfabética em inglês (0x96 Itália, 0x91 Alemanha, 0xAE Ucrânia, 0x9E Holanda).
