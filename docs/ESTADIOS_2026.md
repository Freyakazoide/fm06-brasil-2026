# Estádios, capacidade e cidade de 2026

`aplicar_brasil_2026.py --apply` (`src/fm06patch/estadios.py`) dá a cada clube das
séries o estádio de 2026: nome e capacidade da planilha
`data/brasil/clubes/estadios_2026_modelo.xlsx` (colunas estadio_2026, capacidade,
cidade_2026) e, onde ela estiver vazia, do Sofascore
(`data/brasil/clubes/estadios_sofascore.csv`). A coluna `reputacao` da planilha
vira a reputação do time. O que foi feito fica em
`data/brasil/clubes/estadios_2026_relatorio.txt`.

## Banco (server_db 6.0.2)

| Registro | Campo |
|---|---|
| time ("0A 00") | +19 u32 índice do estádio (São Caetano 2623, Flamengo 1205, São Paulo 1130) |
| estádio (tabela em 0xE80000–0x1000000) | u32 índice da cidade, FF FF FF FF, u32 índice, u32 UID, 00, u32 capacidade, u32 capacidade 2 (Maracanã em 0xEF4AEB: Rio, 1205, 102987, 77000) |
| cidade | u32 índice, u32 UID, 00 00, 2 floats, u8, u8 nação (0xBD) |
| lang_db | u32 UID, u32 tamanho, texto, 00 00 00 ("Anacleto Campanella" 301355, "São Caetano do Sul (SP)" 301034) |

O mesmo índice aparece em registros de cidade (início do arquivo) e em outras
tabelas (0x13xxxxx); só vale um achado único na tabela de estádios.

## Regras

- Clubes com o mesmo estádio em 2026 (Flamengo e Fluminense no Maracanã) ficam
  com um estádio só do FM06.
- O grupo fica com um estádio que ele já usa, se ninguém de fora dele o usa; se
  não (Mineirão do Cruzeiro e do Atlético-MG), um estádio de clube que não
  usamos. O escolhido é renomeado (`STADIUM_NAME_CHANGE` no `brasil_2026.lnc`) e
  recebe a capacidade.
- Cidade: a do FM06 com o mesmo nome "Cidade (UF)", se existir; se não, uma
  cidade sem uso renomeada (`CITY_NAME_CHANGE`).
