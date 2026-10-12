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

## Próximos passos

1. Decodificar os métodos [71] da Série A e os equivalentes da B e da C:
   número de clubes, turnos, acesso e rebaixamento, datas.
2. Primeiro teste de patch numa **cópia** do `fm.exe`: trocar uma constante
   simples (por exemplo, a quantidade de rebaixados) e confirmar no jogo.
3. Planejar o 4º nível (Série D) com code cave.
