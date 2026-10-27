# Ficha C5b — Orçamento de contratações e de salários

- Quem analisou / data: Claude, 2026-10-27 (Ghidra 12.1.4 headless + capstone + memória do jogo aberto)

## Conferido

### Nas finanças do clube não há orçamento

- Os clubes têm finanças do tipo **básico** no `server_db` (`financas.py`). Contei todos os
  clubes do banco original (todas as nações): 8.653 básicos e **nenhum completo** (os 5
  "completos" do varrimento são leituras falsas). Não há registro completo para usar de modelo.
- O leitor do básico (vtable `0x010EF344`, método 2, `0x00A7A1F0`) lê só: u32 saldo (+4),
  u8 marca de "dono rico" (+0xC), u32 (+0x10, versão ≥ 0x127) e um sub-objeto (+0x14).
  O +0x10 vale 0 na maioria dos clubes brasileiros e 3 a 4 milhões em alguns; não é usado na
  conversão abaixo.

### New Game: o objeto completo nasce do saldo

- `0x00A29300` troca o básico pelo completo (0x280 bytes, construtor `0x00A8A7C0`, vtable
  `0x010EFE14`). Do básico passam só o **saldo** (método `0xAC` = `[+4]`) e a marca de dono
  rico (+0xC, que vira o método `0x154`). O construtor zera os orçamentos.
- Depois chama o init (vtable+4, `0x00A87170`), que calcula tudo:
  1. Saldo: método `0xDC` (`0x00A7A4D0`). Se o saldo é diferente de 0 e menor que
     3 × reputação², só sorteia ±10%; senão troca por um valor da tabela `0x01303A80`
     (por faixa de reputação de 500) ajustado por dados da nação. Com dono rico, mínimo
     £25 mi.
  2. **Orçamento salarial** (+0x88) = método `0xC8` (`0x008AB710`), fórmula com a reputação
     do clube e da nação (sem campo no arquivo).
  3. **Orçamento de transferências** (+0x1C, e o restante em +0x20) = `0x00A84780`: base no
     método `0xC4` (`0x008AC550`, fórmula com reputação do clube, da nação e da liga, público
     e situação financeira) e piso de **10%, 15% ou 20% do saldo** quando o saldo passa de
     £50.000 (`0x00A84B72`…`0x00A84BB9`; constantes 0,1 `0xE317B0`, 0,15 `0xE6CD28`,
     0,2 `0xE317A0`, conforme o método `0x18`).
  4. "% da transferência disponibilizada" (+0x24) = `0x00A7FBB0` (80% com saldo ≥ £1 mi ou
     reputação ≥ 5750; 25/50/65% com saldo negativo; −10 se a folha passa do orçamento).
- Toda virada de temporada recalcula o orçamento de transferências (`0x00A87040` chama o
  mesmo `0x00A84780`).

### Objeto completo na memória (New Game de 27/10)

| Clube | +0x1C/+0x20 transf. (£) | +0x24 % | +0x88 salarial/sem (£) | +0x90 folha/sem (£) |
|---|---|---|---|---|
| Flamengo | 50.000 / 50.000 | 75 | 413.803 | 520.578 |
| Corinthians | 4.700.000 / 4.700.000 | 75 | 341.132 | 373.311 |
| Fluminense-PI | 12.943 / 12.943 | 40 | 9.600 | 4.388 |

- +0x90 conferido com a tela: 520.578 × 4 × 5,08 = R$ 10,58 mi/mês (folha do Flamengo).
- +0x88 é hipótese (orçamento salarial semanal): 413.803 × 4 × 5,08 = R$ 8,4 mi/mês, perto
  dos R$ 8,5 mi da tela.
- Flamengo não bate com o piso de 10% do saldo: quem regrava é o FINANCE_MANAGER (abaixo).

### A tabela do FINANCE_MANAGER (conferido com o vigia 2)

- Logo depois da troca das finanças, `FINANCE_MANAGER::setup()` (`0x006D4400`) percorre uma
  tabela do `server_db` e, por registro: troca as finanças do clube, cria o empréstimo
  (`0x006CF960`, valor e prazo do registro) e grava o **orçamento de transferências fixo**
  por cima do calculado (`0x006D45A1`, `mov [ecx+0x1C], edi`). Só se o clube não tiver
  dono rico (+0xC).
- No banco original: `u32` quantidade em 0x13D8555 (3.536) e registros de 24 bytes
  `u8, u32 time, u32 empréstimo £, u16 meses, u32 orçamento £, u8 tipo, u32 índice, u32 −1`.
- "time" = índice do registro do time do clube (o u32 antes de `UID do clube, 0A 00` + 1),
  resolvido para o clube por `0x00A18CD0` (time+0x38). Corinthians 287 (£4,7 mi),
  Flamengo 290 (£50 mil, e outro registro com o empréstimo de £22,5 mi em 103 meses, os
  R$ 115 mi do jogo), Chelsea 544 (£100 mi), Arsenal £153,3 mi de empréstimo (o estádio).
- O orçamento salarial não está na tabela: sai da fórmula (`0x008AB710`) e muda de novo
  quando o técnico assume (`0x006F4F4C`, Flamengo 495.456 → 409.680/sem).

## Consequência

O orçamento de transferências de 2026 vai direto no banco, na tabela do FINANCE_MANAGER
(`fm06patch/orcamentos.py`, chamado pelo `aplicar_brasil_2026.py` com a aba Estrutura): não
precisa de patch no exe. Clube que tem registro recebe o valor nele (o do empréstimo, se
houver); os 5 clubes da planilha sem registro ficam com o que sobra quando os dois registros
de outro clube da planilha viram um. Mesmo tamanho de arquivo, nenhum clube fora da
planilha muda. Vale para o New Game; nas temporadas seguintes o jogo recalcula pela fórmula.

Fica para depois: o orçamento salarial (fórmula + diretoria) e os empréstimos de 2005 que
continuam na tabela (Flamengo £22,5 mi; a planilha só tem a dívida do Flamengo,
R$ 174 mi).

## Diário

- 27/10, vigia 1 (`workspace/rea/tools/vigia_orcamento.py`, parada em `0x00A8727B` com filtro
  de saldo): **sem efeito**, não parou nenhuma vez durante o New Game com o Flamengo.
  Leitura da memória depois (157 objetos de finanças completas): clube+0x14 = UID do jogo
  (Flamengo 322). Flamengo de novo com transferências £50.000 (saldo £26,18 mi, salarial
  423.607/sem); Corinthians de novo £4.700.000 (saldo £17,96 mi); Fluminense-PI £13.981.
  Os valores redondos se repetem entre New Games, embora o saldo seja sorteado.
- 27/10, vigia 2: conta as passagens em `0x00A29300`, `0x00A8727B`, `0x00A87040` e
  `0x00A84780`, e anota as escritas em +0x1C/+0x88 do Flamengo. **Deu certo**: 157 inits;
  no Flamengo o init deu £5.590.221 (20% do saldo de £27,95 mi, fora da faixa do vigia 1) e
  `0x006D45A4`/`0x006D45A1` (setup do FINANCE_MANAGER) gravou £50.000. Depois, salarial
  495.456 → 409.680 em `0x006F4F4C`.
- 27/10, teste 1 do orçamento (`orcamentos.py`): 40 clubes da aba Estrutura, 35 no próprio
  registro e 5 em registros que sobraram. Instalado com `aplicar_tudo --rapido`; no
  `server_db` do jogo a tabela está em 0x13DEB4E (o histórico muda o tamanho antes dela),
  63 registros diferentes do original: Flamengo £8.287.402 (R$ 42,1 mi) no registro do
  empréstimo, Corinthians £5.905.512 (R$ 30 mi), Chapecoense £1.279.528 (R$ 6,5 mi),
  Chelsea igual. New Game: **deu certo**. Tela de finanças: Flamengo R$ 42.100.001
  (época e restante, 75%), Chapecoense R$ 6.500.002 (90%), os dois iguais à aba Estrutura.
