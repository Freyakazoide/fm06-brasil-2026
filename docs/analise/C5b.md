# Ficha C5b — Orçamento de contratações e de salários (em andamento)

- Quem analisou / data: Claude, 2026-10-27 (Ghidra 12.1.4 headless + capstone + memória do jogo aberto)

## Conferido

### No banco não há orçamento

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
- Flamengo não bate com o piso de 10% do saldo (£21,7 mi → pelo menos £2,17 mi). Hipótese:
  alguém regrava o orçamento depois do init (por exemplo, a diretoria ao contratar o
  treinador humano). Não conferido.

## Consequência

Não existe campo de orçamento para gravar no banco, nem como passar o valor do arquivo para
o objeto: os orçamentos são sempre calculados no New Game e de novo a cada temporada. O que o
mod controla hoje (saldo, público, reputação, dono rico) só mexe nas entradas da fórmula.

Caminhos:

1. **Patch no `fm_brasil.exe`**: depois do init (`0x00A87170`), procurar o clube numa tabela
   gravada no exe (UID → orçamento de transferências e salarial da aba Estrutura) e
   sobrescrever +0x1C, +0x20 e +0x88. Vale só para a 1ª temporada; da 2ª em diante volta a
   fórmula do jogo.
2. **Só as entradas**: deixar a fórmula e ajustar saldo/reputação. Barato, mas o orçamento fica
   longe da planilha (e mexer no saldo para isso estraga o saldo de 2026).

Antes do caminho 1, falta conferir quem regrava o orçamento do Flamengo depois do init.
