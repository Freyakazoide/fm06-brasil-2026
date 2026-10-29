# Ficha C1b — Patrocínio dos clubes

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
- Renovação: `0x00A7E410` (chamado de `0x008AA580`) compara o ano do fim (+0xE) com o ano
  atual (`0x014EAB3A`); quando acabou, chama o mesmo gerador `0x00AAEDF0` e paga o valor
  novo (método 0xA0 das finanças). Então o contrato novo já segue a reputação do clube na
  hora da renovação: quem sobe ganha proposta melhor, quem cai e perde reputação recebe
  menos. Durante o contrato o valor não muda (não há cláusula de rebaixamento).

## Consequência

Dá para gravar o patrocínio de 2026 no banco: no registro do clube, trocar o u32 0 depois das
finanças por 1 e inserir os 13 bytes do contrato (valor em libras, fim com o ano − 20,
anos). O arquivo cresce 13 bytes por clube, então entra no fim do `aplicar_brasil_2026.py`,
depois das etapas que mudam o tamanho, lendo as posições no banco já alterado.

## Decidido (27/10)

- A `patrocinadores_2026.xlsx` só tem valor em 10 dos 40 clubes e nenhuma data. O usuário
  vai preencher os contratos reais em `data/modelos/patrocinio_jogo_2026.xlsx` (aba
  Contrato_jogo: 156 clubes das séries, com o que o jogo inventa hoje em cinza para
  comparar a escala). Linha sem valor ou sem fim fica com o contrato do jogo.
- Padrão de crescimento/queda: o jogo já renova pela reputação (acima). Calibrar a escala
  da fórmula para o Brasil de 2026 seria um patch nas constantes de `0x00AAEDF0`: fica
  para depois de ver os primeiros contratos no jogo.

## Diário

- 27/10: leitura da memória do New Game (Flamengo) e do código; nenhum teste no jogo ainda.
- 29/10, teste 1 (`patrocinio.py`): planilha com os 156 clubes preenchidos pelo usuário.
  Instalado com `aplicar_tudo --rapido`; no `server_db` do jogo os 156 clubes têm a marca 1 e
  o contrato (Flamengo £52.854.331 = R$ 268,5 mi, fim dia 365 de 2008 = 31/12/2028, 3
  anos; Corinthians R$ 150 mi até 2029). A tabela de orçamentos continua legível (3.536).
  New Game (29/10): **deu certo** na tela. Flamengo "Contrato de 3 anos no valor de R$268M por
  época. Termina a 2028"; Goiás "3 anos, R$17,99M, termina 2028" (planilha R$ 18 mi).
  Orçamento de transferências igual (R$ 42.100.001).
- Em aberto: receitas do 1º mês do Flamengo caíram de R$ 10,9 mi (contrato do jogo) para
  R$ 4,7 mi. O patrocínio não entra aí: o init não paga o contrato (nem o gerado; a
  Chapecoense tinha R$ 0 de receita com o contrato do jogo). Quem paga é `0x00A7E410`,
  chamado por `0x008AA580` (virada da temporada, hipótese), que soma o valor inteiro no
  saldo e nas receitas (`0x00A7C8D0`: +4, +0x7C, +0x110, +0x1D8). Falta ver a tela de
  receitas e o pagamento depois do início da temporada.
- 29/10, tela de receitas: os R$ 4,7 mi do 1º mês são "Prêmios em Dinheiro" (não é
  patrocínio). Em 31/01/2026, "Patrocínio" ainda R$ 0 (saldo R$ 101 mi; salários
  R$ 13,2 mi/mês).
- Quem paga: `0x008AA580` é o método 0xF0 (60) das finanças completas (vtable
  `0x010EFE14`). Faz o balanço do ano (`0x006D1600`), chama `0x00A7E410` (paga o contrato
  e renova se acabou; notícia com `0x00579700` tipo 6) e outras rotinas do fim do ano. Não
  é chamado no New Game. Na memória em 31/01 (Flamengo e Corinthians): +0x270 (data do
  último balanço?) = 1900 e +0x268 = dia 54 de 2006 (24/02/2026, hipótese: próxima data
  das finanças). Falta ver no jogo quando o patrocínio cai.
- 29/10, começo de março: "Patrocínio" ainda R$ 0 (saldo R$ 94,65 mi). A data 24/02 não era.
- Quem chama o método 0xF0: `0x006D0870(nação)` percorre os clubes da nação (CLUB+0xDC) e
  chama 0xF0 nas finanças de cada um; é chamado só por `0x00AD3D4B` (`0x00AD39B0`), quando o
  evento do calendário da nação é o tipo 9 (`cmp byte [esi+0x2D], 9`, hipótese: fim da
  temporada). Então o patrocínio é pago uma vez por ano, no fim da temporada, já com o
  valor da temporada seguinte (ou o do contrato renovado). A 1ª temporada do save não recebe
  patrocínio: é assim também no jogo original, com o contrato gerado.
- 29/10, decidido: pagar a 1ª temporada no New Game, para todos os clubes. Patch
  `patrocinio_inicio` (`patrocinio.exe_swaps`): `0x00A872E9` `75 05 E8 40 1E FA FF` (jne +
  call do gerador) -> `call 0x015BA000` + 2 nop; o desvio na `.fm26` (+0x6000) gera o
  contrato se faltar e, com FINANCE+0x7C ainda 0, paga `[contrato+4]` por `0x00A7C8D0`
  (+4 saldo, +0x7C, +0x110 e +0x1D8 receitas). Nada no init mexe em +0x7C antes do desvio.
  Instalado (`aplicar_tudo --rapido`; a 1ª tentativa falhou com o exe ainda preso logo
  depois de fechar o jogo). New Game (29/10): **deu certo**. Flamengo: Receitas "Patrocínio"
  R$ 268M em Este Mês e Esta Época (uma vez só), Prêmios em Dinheiro R$ 6,27 mi, saldo
  R$ 361 mi; contrato "3 anos, R$268M, termina 2028". O orçamento de transferências fica
  R$ 42.100.001 (o da aba Estrutura, gravado pelo FINANCE_MANAGER depois do init).
