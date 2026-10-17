# Calendário 2026: levantamento e proposta

Objetivo: todas as competições que envolvem clubes brasileiros sem conflito de
datas, seguindo o calendário da CBF de 2026.

## Como as datas ficam no fm.exe

Cada competição monta suas fases no método 71 da vtable (ver
`docs/reversing/competitions.md`). As datas são números passados direto às
funções abaixo; **o mês começa em 0** (0 = janeiro) e o ano é relativo
(`2000` = ano da temporada, `2001` = ano seguinte).

| Função | Argumentos | Uso |
|---|---|---|
| `0x00B08360` | (tipo, dia, mês, 2000) | início de uma fase de liga |
| `0x00B08470` | (tipo, dia, mês, 2000) | fim de uma fase de liga |
| `0x00B3B550` | (hora, dia, mês, 2000, x) | sorteio de um mata-mata |
| `0x00B3B760` | (hora, dia, mês, 2000, tipo, …) | data de uma rodada de mata-mata |
| `0x00ACFFF0` | (dia, mês) | **virada da temporada do país** |

Ferramenta do levantamento: varredura do método 71/72 de cada competição e das
funções do módulo que ela chama, procurando chamadas com `2000`/`2001`.

## Virada da temporada

`bra_get_settings` (`0x00BB2710`) chama `0x00ACFFF0(dia, mês)`: a temporada
do Brasil vira em **2 de janeiro** (a Alemanha, para comparar, em 20 de
junho: `0x00ACFFF0(20, 5)`). Patch `virada_1_janeiro`: 1º de janeiro
(`0x00BB272F`: `6A 02` → `6A 01`).

## Como uma liga distribui as rodadas

A montagem da fase registra "janelas" de datas com `0x00B0EE30`, cada uma
com início (`0x00B08360`), fim (`0x00B08470`) e dias/horários dos jogos
(`0x00B085F0`, `0x00B08D90`). A Série A original registra duas: 6/8–10/12
(com o campo `+0x20` = 26) e 30/4–10/12 (com o número de turnos,
`0x00B08440`). A Bundesliga registra uma só (5/8–19/5 do ano seguinte) e
mesmo assim tem pausa de inverno, então a pausa vem de outro lugar (a
investigar: `0x00B0EE30` monta as datas e consulta o país, métodos
`0x208`). Para a pausa da Copa: primeiro ver no jogo se a Série A já para
durante a Copa do Mundo de 2006 do FM06.

## O que o FM06 tem hoje (temporada 2006, sem o mod)

| Competição | Classe | Datas no FM06 |
|---|---|---|
| Estaduais (genérico: SP, MG e outros) | `BRA_STATE_LEAGUE` | início 16/1; fim 19/2, 19/3 ou 23/4 conforme o estado (tabela em `0x00BB3DF0`); mata-mata depois |
| Baiano | `BRA_STATE_BAHIA` | 16/1–27/2; mata-mata 28/2–9/4 |
| Carioca | `BRA_STATE_RIO` | Taça Guanabara 16/1–13/2 (final 20/2); Taça Rio 27/2–2/4 (final 9/4); finais até 16/4 |
| Paraibano | `BRA_STATE_PARAIBA` | 16/1–5/3; 12/3–16/4; final 23/4 |
| Paranaense | `BRA_STATE_PARANA` | 16/1–19/3; mata-mata 26/3–16/4 |
| Pernambucano, Gaúcho, Catarinense, Paraense, Tocantinense | `BRA_STATE_*` | 16/1 até março/abril (algumas datas vêm de tabela) |
| Copa do Brasil | `BRA_CUP` | 6 rodadas: 2/2, 2/3, 30/3, 20/4, 25/5, 15/6 |
| Libertadores | `SAM_LIBER_CUP` | sorteio 15/1; grupos fev–mai; mata-mata até julho |
| Sul-Americana | `SAM_SUD_CUP` | sorteio 19/7; rodadas 9/8, 23/8, 13/9, 18/10, 22/11, 6/12 |
| Recopa | `SAM_SUPER_CUP` | sorteio 15/1 |
| Série A (original) | `BRA_NAT_FIRST` | 30/4–10/12, returno a partir de 6/8 |

## O que o mod já mudou

| Série | Datas hoje no mod |
|---|---|
| A | 28/1–2/12; returno a partir de 6/8 (sem pausa da Copa) |
| B | 21/3–15/11; playoff sorteado 20/11, jogos 22/11 e volta |
| C | 1ª fase 5/4–23/8; grupos 6/9–1/11 |
| D | grupos 5/4–9/8; mata-mata 16/8–2/9; fase final 16/9–28/10 |

## Calendário da CBF para 2026

| Competição | Datas |
|---|---|
| Estaduais | 11/1–8/3 (11 datas) |
| Série A | 28/1–2/12 |
| Série B | 21/3–28/11 |
| Série C | 5/4–25/10 |
| Série D | 5/4–13/9 |
| Copa do Brasil | 18/2–6/12; clubes da Série A entram na 5ª fase; final em jogo único |
| Libertadores | fase preliminar a partir de 18/2; grupos a partir de abril; final 28/11 |
| Sul-Americana | 8/4–21/11 |
| Recopa | 18 e 25/2 |
| Pausa da Copa do Mundo | 1/6–20/7 |

## Conflitos atuais

1. **Estaduais × Série A**: no FM06 os estaduais vão até abril; a Série A do
   mod começa em 28/1. O jogo empurra rodadas (em fevereiro de 2007 havia
   rodadas da A em cima dos estaduais).
2. **Estaduais × B, C e D**: os estaduais do FM06 ainda estão em andamento
   quando B (21/3), C e D (5/4) começam; foi isso que empurrou rodadas para
   depois da data de fim nos testes.
3. **Copa do Brasil**: termina em junho no FM06; em 2026 vai até dezembro.
4. **Libertadores**: termina em julho no FM06; em 2026 a final é 28/11.
5. **Sem pausa da Copa do Mundo** na Série A.

## Proposta (a aprovar)

| Competição | Proposta |
|---|---|
| Virada da temporada | 1º/1 |
| Estaduais | 11/1–8/3 em todos os estados (datas de início, fim e mata-mata comprimidas) |
| Série A | turno 28/1–31/5; pausa 1/6–20/7; returno 22/7–2/12 |
| Série B | pontos corridos 21/3–15/11; playoff 21/11 e 28/11 |
| Série C | 1ª fase 5/4–23/8; grupos 6/9–18/10; final 25/10 (quando existir) |
| Série D | 5/4–13/9, com folga; ajustar grupos e mata-mata para não sobrepor |
| Copa do Brasil | rodadas espalhadas de 18/2 a 6/12 |
| Libertadores e Sul-Americana | trazer para o calendário de 2026 (vale para todos os países da América do Sul) |

Pontos a decidir:

- A pausa da Copa do Mundo se repete todo ano (as datas no fm.exe são fixas)
  ou fica só a data de 2026 e as outras temporadas jogam sem pausa?
- Formato dos estaduais: só comprimir as datas (rodadas no meio da semana) ou
  também reduzir o formato para caber em 11 datas, como a CBF fez?
- Libertadores e Sul-Americana: mudar agora ou depois, junto com as vagas
  continentais?

## Pausa da Copa do Mundo (Série A)

Testes no jogo (temporada 2006, Copa do FM06 de 07/06 a 09/07):

| Versão | Resultado |
|---|---|
| original do mod (12 rodadas espalhadas até 06/08, 26 na janela final) | jogos em 10/06, 24–25/06, 28/06, 15–16/07: o jogo **não** pausa sozinho |
| `exp_a_copa_1`: janela final de 19 rodadas a partir de 22/07 | jogos em 21/05, 04/06, 11/06, 25/06, 02/07, 16/07: o turno se espalha até a janela final |
| `exp_a_copa_2`: igual, e a janela da temporada termina em 31/05 | último jogo do turno em 28/05, volta em 23/07: **funciona** |

Conclusão: a janela final recebe as últimas N rodadas (word em `+0x20` do
modelo de datas) e as demais ficam entre o início e o fim da janela da
temporada.

Patch `serie_a_calendario_copa` (`src/fm06patch/calendario.py`), no lugar
de `serie_a_datas_2026`: escolhe as datas pelo ano da temporada
(competição `+0x9C`, ano % 4 == 2 = ano de Copa: 2006, 2010… no FM06, os
mesmos de 2026, 2030…):

| | Turno (19 rodadas) | Returno (19 rodadas) |
|---|---|---|
| Ano de Copa | 28/01–31/05 | 22/07–02/12 |
| Outros anos | 28/01–14/06 | 21/06–02/12 |

## Copa do Brasil

FM06 original (`BRA_CUP`, montagem `0x00BBAD30`): mata-mata de 64 em 6
rodadas (2/2, 2/3, 30/3, 20/4, 25/5, 15/6). Participantes (`0x00BB9430`):
classificados da temporada anterior (ou lista inicial), clubes dos
estaduais e, para completar 64, Séries A, B e antiga C (`0x00ACD160`, cdecl
`(ID, lista, máximo, -1, 1, -1, 1)`).

Patch `copa_do_brasil_2026` (`src/fm06patch/copa_do_brasil.py`), da 3ª fase
de 2026 em diante:

| Fase no jogo | Rodadas | Clubes | Datas |
|---|---|---|---|
| 1 (sem a Série A) | 3ª fase (código 6), 4ª fase (código 7) | 48 → 24 → 12 | 11/3, 18/3 |
| 2 | 5ª fase, oitavas, quartas, semifinal, final | 12 + 20 da Série A = 32 | sorteio 18/4; 26/4, 1/8, 26/8, 1/11, 6/12 |

- Participantes da fase 1: os mesmos critérios, filtrando os clubes da Série
  A (`TEAM+0x54`), até 48, completando com Série B, nova C e Série D.
- Vencedores da rodada 7 da fase 1 → fase seguinte (`0x00B45500(7, 0, {…0xA7…})`).
- Método 72: com a fase 1 terminada, `0x00AC73D0(0, 0)` + `0x00B3E6E0` juntam
  os 12; `0x00ACD160(Série A, lista, 20, …)` acrescenta a Série A;
  `0x00B3EF00` + `0x00B44060(1, …)` criam o mata-mata da fase 2.
- Ainda como no FM06: ida e volta em todas as rodadas (inclusive as que em
  2026 são jogo único) e a regra do 2º jogo de cada rodada.

Testes:

- Teste 1: fase 1 jogada (48 clubes, sem a Série A): 8/3 e 22/3, 25/3 e 8/4
  (ida e volta; jogos adiados por finais de estadual em 9, 11 e 21/3).
- Probe em 16/4: fases previstas 2, criadas 2; fase 2 com 32 clubes, mas sem
  jogos até 6/5. Causa: a fase 2 nasce no meio da temporada e a 1ª rodada da
  Copa não tinha data de sorteio (no original os 64 já são conhecidos no
  início). Correção: sorteio `0x00B3B550(0x4B0, 18, abril, 2000, 4)` na 1ª
  rodada da fase 2, como no mata-mata da antiga C.
- Teste com o sorteio em 18/4: ainda sem sorteio até 10/5. Hipótese: a 1ª
  rodada da fase 2 usava a configuração da 2ª rodada original (flags 0x401,
  `+0x46` = 0, "clubes vêm da rodada anterior"); voltou à de 1ª rodada
  (0x8403, `+0x46` = clubes da fase), com o sorteio mantido.
- Teste com a 1ª rodada da fase 2 na configuração de 1ª rodada: **funciona**
  (Vasco na Copa do Brasil em 26/4 e 10/5). O nome da rodada aparece como
  "2ª Elim." (código 7).

## Libertadores e Sul-Americana

IDs: Libertadores 0x1900F, Sul-Americana 0x4D87F, Recopa 0x19012.

- Participantes da Libertadores (`0x00C06710`, método 69): `0x00C06440(país,
  lista, N)` pega, de cada país, os clubes com `TEAM+0xB4` = Libertadores
  (gravado por `0x00A1CE70(competição, byte)`). N: Argentina (0x671) 5,
  **Brasil (0x673) 5**, demais 3, inclusive **México (0x17B)**. IDs de país em
  ordem alfabética: 0x671 ARG, 0x672 BOL, 0x673 BRA, 0x674 CHI, 0x675 COL,
  0x676 ECU, 0x677 PAR, 0x678 PER, 0x679 URU.
- Como `0x00C06440` completa cada país: (1) os marcados com `TEAM+0xB4`
  (só URU, CHI, PER e COL marcam, no fim do campeonato deles); (2) México:
  `0x00C05000`, que espera a competição mexicana 0x21329 terminar (se não
  terminou, a Libertadores adia a montagem); (3) **Brasil: `0x00C05180`, o
  campeão da Copa do Brasil (0x1901B)**; (4) participantes antigos do país
  (+0x118); (5) o resto por `0x00ACD160(-1, lista, falta, país, …)`, que
  ordena pelo nível da divisão e pela posição final (`TEAM+0x60`,
  comparador `0x00A1D110`), ou seja, **os primeiros da Série A anterior**.
  O campeão da Libertadores entra antes, fora da conta do país. Total: 38.
- Montagem da 1ª fase: preliminar (`0x00C05260`) com 12 clubes, o pior de
  cada país (México incluído) + 1 do país do campeão; grupos (`0x00C05430`,
  m72 com a preliminar terminada) com o resto por país (ARG 4, BRA 4, demais
  2) + os 6 vencedores, em 4 potes de 8 pelo país (pote 1 ARG/BRA e o
  campeão; 2 COL, MEX, PAR, URU; 3 BOL, CHI, ECU, PER; 4 VEN + preliminar).
- Patch `libertadores_vagas_2026` (`src/fm06patch/libertadores.py`): Brasil
  5 -> 7, Argentina 5 -> 6, México 3 -> 0 (total 38). Preliminar: a vaga do
  México vai para a Argentina. Grupos: Brasil 6, México 0; um desvio passa
  os 2 brasileiros piores do pote 1 (10) para o pote 2 (6). Primeira versão
  só com as vagas: a preliminar ficou com 11 clubes, o 11º foi pareado com
  lixo e o jogo caiu em janeiro de 2006 (dump: `0x00C05260` -> ... ->
  `0x00B007C0` lendo o visitante do jogo).
- Sul-Americana: patch `sul_americana_2026` (`src/fm06patch/sul_americana.py`),
  mata-mata de 28 clubes em 6 rodadas no lugar dos 34: 1ª fase com 16 clubes
  dos 8 países menores (2 por país, confronto do mesmo país), 2ª fase com os
  8 vencedores, oitavas com Argentina 6 + Brasil 6 + 4 da 2ª fase, quartas,
  semi e final única. Brasil 6 pela tabela da Série A, sem quem está na
  Libertadores (exclusão em `0x00C06C42` passa a valer para BRA, ARG e PER);
  México e EUA 0; o campeão anterior não é inscrito à parte. O construtor
  (`0x00C05F10`) monta a competição em 1/8 com temporada de julho a
  dezembro. Teste: montar em 25/1 com temporada de janeiro fez o New Game
  (1/7/2005) montar na hora a edição de 2005 com datas de abril já
  passadas; a de 2006 nunca foi montada. Por isso fica de agosto a novembro:
  sorteio 3/8, 1ª fase 9/8, 2ª fase 23/8, oitavas 13/9 (+7 dias), quartas
  4/10, semifinal 25/10, final 21/11 (jogo único, SECTION_VA+0x4280),
  rodadas na quinta. Chaveamento da 1ª fase (`0x00C05FD0`) por tabela fixa
  (SECTION_VA+0x4200/0x4240).
- Datas da Libertadores: a competição é montada em 21/1 (`0x00C0639C`). A
  tabela do calendário internacional (`[0x014EB678]+0x60C`, entradas de
  0x18 bytes por `0x00AF6490`) é preenchida pelo método 0x124 de cada
  competição; na Libertadores `0x00C047D0`: preliminar (rodada 0x1C), 10
  datas de grupo (0x49, tipos 0–9; grupos A–D usam 0, 2, 4, 5, 7, 9 e E–H
  1, 3, 4, 6, 8, 9), oitavas (7) e quartas (0x11), todas quarta 21h em
  datas de 2000. O jogo guarda a semana e o dia da semana (a data anda
  ~1 dia por ano). Semifinal e final ficam em `0x00C07980` com datas fixas e
  troca em ano de Copa. Patch `libertadores_datas_2026`: preliminar 22/2 e
  1/3; grupos 5, 12, 19/4, 3, 10, 24/5 (E–H na quinta); oitavas 9 e 16/8
  (sorteio 3/6); quartas 13 e 20/9; semifinal 18 e 25/10; final única em
  28/11 (rodada +0x34 = 1 no lugar da conta do ano de Copa).
- Patch `sul_americana_datas_2026`: mata-mata de 6 rodadas em 15/4, 12/8,
  9/9, 14/10, 4/11 e final 21/11 (sorteio 1/4).
