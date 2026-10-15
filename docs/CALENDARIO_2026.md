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
| 2 | 5ª fase, oitavas, quartas, semifinal, final | 12 + 20 da Série A = 32 | 22/4, 1/8, 26/8, 1/11, 6/12 |

- Participantes da fase 1: os mesmos critérios, filtrando os clubes da Série
  A (`TEAM+0x54`), até 48, completando com Série B, nova C e Série D.
- Vencedores da rodada 7 da fase 1 → fase seguinte (`0x00B45500(7, 0, {…0xA7…})`).
- Método 72: com a fase 1 terminada, `0x00AC73D0(0, 0)` + `0x00B3E6E0` juntam
  os 12; `0x00ACD160(Série A, lista, 20, …)` acrescenta a Série A;
  `0x00B3EF00` + `0x00B44060(1, …)` criam o mata-mata da fase 2.
- Ainda como no FM06: ida e volta em todas as rodadas (inclusive as que em
  2026 são jogo único) e a regra do 2º jogo de cada rodada.
