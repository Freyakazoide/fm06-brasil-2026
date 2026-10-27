# Ficha C1b — Patrocínio dos clubes (em andamento)

- Quem analisou / data: Claude, 2026-10-27 (Ghidra 12.1.4 headless + capstone + memória do New Game)
- Pergunta (docs/ANALISE_DE_CODIGO.md): de quem é a lista de patrocínios e onde o jogo calcula
  o dinheiro do patrocínio.

## Conferido

### O contrato fica no clube (CLUB+0x11C)

- Memória do New Game de 27/10 (Flamengo, tela "Contrato de 5 anos no valor de R$9,71M por
  época. Termina a 2028"): CLUB+0x11C aponta para um objeto de 0x14 bytes
  `00 00 00 00 | b4 2e 1d 00 | dc 38 16 01 d4 00 d8 07 | 05`:
  - +0 u32 = 0;
  - +4 u32 valor por temporada em libras (1.912.500 × 5,08 = R$ 9,7155 mi);
  - +8 DATE do fim (vtable `0x011638DC`, u16 dia 212, u16 ano 2008);
  - +0x10 u8 anos de contrato (5).
- O jogo mostra o ano + 20: data atual na memória (`0x014EAB34`) = dia 359 de 2005, o
  mesmo deslocamento do `year_shift` −20 do mod (2008 → "2028").
- A lista SPONSOR da ficha C1 (`0x014EAA74`) é a das empresas; a tela usa um índice nela
  só quando o contrato tem empresa (`0x00813703`).

### O banco pode trazer o contrato; sem ele o jogo gera

- O leitor do clube (`0x00A31C70`), logo depois das finanças (tipo, saldo, u8, u32, DATE),
  lê um u32 para CLUB+0x11C (`0x00A3223D`); se não for 0, cria o objeto de 0x14 bytes e lê
  `0x00AAED20`: u32 (+0), u32 valor (+4), DATE (u16 dia, u16 ano) e u8 anos (+0x10).
- No banco original os 667 clubes brasileiros têm 0 aí (em todo o banco, nenhum contrato
  legível).
- No New Game, o init das finanças (`0x00A87170`) só chama o gerador `0x00A29130` quando
  CLUB+0x11C é 0. O gerador (`0x00AAEDF0`) calcula o valor pela reputação do clube e da
  nação (com casos por nação), sorteia os anos (2 a 5, +1 acima de £5 mi) e põe o fim na
  data atual + anos; o +0 fica 0.

## Consequência

Dá para gravar o patrocínio de 2026 no banco: no registro do clube, trocar o u32 0 depois das
finanças por 1 e inserir os 13 bytes do contrato (valor em libras, fim com o ano − 20,
anos). O arquivo cresce 13 bytes por clube, então entra no fim do `aplicar_brasil_2026.py`,
depois das etapas que mudam o tamanho, lendo as posições no banco já alterado.

## Falta decidir

- A planilha `patrocinadores_2026.xlsx` só tem valor em 11 dos 40 clubes (todos "master") e
  nenhuma data de início ou fim.

## Diário

- 27/10: leitura da memória do New Game (Flamengo) e do código; nenhum teste no jogo ainda.
