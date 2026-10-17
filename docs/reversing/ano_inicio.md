# Ano de início do jogo (New Game)

Análise estática do `fm.exe` (endereços virtuais; arquivo = endereço − 0x400000).

## De onde vem a data

Não há um campo único de "data de início": ela vem de constantes no exe e
do dia/mês de início da temporada de cada país.

- Data atual do jogo: `SI_DATE` em `0x14EAB34` (+4 dia do ano, base 0,
  = `0x14EAB38`; +6 ano = `0x14EAB3A`; +8 horário). Data de início do mundo:
  `0x14EAB40`.
- `server_db.dat`, cabeçalho: `0x0D–0x11` e `0x12–0x16` = 1/7/2005 (horário,
  u16 dia do ano, u16 ano); anos em `0x10` e `0x15`.
- New Game (`0x464070`): depois de carregar o banco, a data atual vira
  1/1/2005 (`0x464298 push 0x7D5`).
- Escolha do início (`0x82E940(país, ajuste)`): dia e mês do início da
  temporada do país; ano `0x7D6 + ajuste` (meses jan–jun, `0x82E9E6`) ou
  `0x7D5 + ajuste` (jul–dez, `0x82EA4A`). Ajuste 0 ou −1 (`0x8316D5`,
  `0x82F75B`).
- Criação do jogo (`0x463310`): copia para `0x14EAB40` e chama
  `0xAE2A00`; `0xAD0C30 → 0xAD0B70 → 0xAD00C0` gravam o ano da temporada de
  cada país (2005/2006 fixos: `0xAD0C3E`, `0xAD012E`, `0xAD0135`,
  `0xAD0177`, `0xAD0196`).

## O que mudar para começar em 2026 de verdade

1. ~15 constantes de início no exe (acima e `0xACF813`, `0x4045D6`,
   `0x404619`, `0x40461F`, `0x404626`).
2. Anos do cabeçalho do `server_db.dat`.
3. Código que testa o ano 2005/2006 (Brasil `0xBB322F`, `0xBB02A7`,
   `0xBB2020`; Libertadores `0xC068EA`; dezenas em outros módulos) e,
   principalmente, `sub reg, 0x7D5` usado como índice de tabela por ano
   (`0xBC5F20`, `0xBD9167`, `0xBE7CAA`, `0xBE8C78`, `0xC006B1`, `0xC0F3F4`,
   `0xC117ED`, `0xC20872`, `0xC2FDD5`, `0xC3E5ED`; com 0x7D4: `0xC17FC2`,
   `0xC26ED7`, `0xC29BB6`, `0xC31DA7`, `0xC32A77`, `0xC32E44`, `0xC3543D`,
   `0xC36D07`, `0xC447B2`): fora do intervalo, leitura de lixo ou queda.
4. ~306 `push 0x7D5` e 47 `push 0x7D6` com datas fixas de jogos
   (`0xB117A0`, eliminatórias em `0xC30000–0xC3FFFF`) e ~778 `push 0x7D4`
   para `0xC58AD0` na inicialização estática (~`0xE10000`).
5. Todas as datas absolutas dos bancos (nascimento, contratos,
   transferências, histórico) + 21 anos; formatos dos registros a mapear.

## Alternativa: somar só na exibição

Manter o motor em 2005/06 e somar ao ano exibido (`SI_DATE` para texto
`0xC665F0`, data curta `0xC56FA0`, nomes de temporada a partir de
`+0x9C`). Para o calendário brasileiro (temporada 2006 do motor = 2026), o
ajuste seria +20: 2006 e 2026 são anos de Copa e não bissextos, 2008 e 2028
bissextos. Os dias da semana não batem (1/1/2006 domingo, 1/1/2026 quinta).
As idades seguem pelo `year_shift` do injetor (motor − 2026).
