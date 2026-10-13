# Regras do Brasileirão 2026 (referência para o mod)

Fonte: regulamentos da CBF para 2026, conferidos pelo usuário. São 156 clubes
em quatro divisões nacionais. Os participantes estão em
`data/brasil/series_2026.csv`.

O mod precisa reproduzir os participantes, as datas e também os mecanismos
de classificação, acesso e rebaixamento.

## Visão geral

| Divisão | Clubes | Início | Término | Acesso | Rebaixamento |
|---|---|---|---|---|---|
| Série A | 20 | 28/01/2026 | 02/12/2026 | — | 4 |
| Série B | 20 | 21/03/2026 | 28/11/2026 (fim dos playoffs) | 4 | 4 |
| Série C | 20 | 05/04/2026 | 25/10/2026 | 4 | 2 |
| Série D | 96 | 04–05/04/2026 | 13/09/2026 | 6 | não há Série E |

Os calendários estão sujeitos a ajustes da CBF.

## Série A

- 20 clubes, turno e returno, 38 rodadas, 380 jogos. 3 pontos por vitória.
- Campeão: o 1º colocado, sem final.
- 17º ao 20º: rebaixados direto à Série B de 2027, sem playoff.

Classificação continental (2027):

| Colocação | Destino |
|---|---|
| 1º ao 4º | Libertadores, fase de grupos |
| 5º | Libertadores, fase preliminar |
| 6 melhores ainda não classificados à Libertadores | Sul-Americana |
| 17º ao 20º | rebaixamento |

- Copa do Brasil: campeão vai à fase de grupos da Libertadores e vice à fase
  preliminar. Vaga duplicada passa adiante pela classificação do Brasileirão
  (artigo 6º).
- O campeão brasileiro joga a Supercopa Rei de 2027.

## Série B

- 20 clubes, turno e returno, 38 rodadas. 1º colocado é o campeão.
- 17º ao 20º: rebaixados à Série C de 2027.
- Acesso: 1º e 2º sobem direto. Outras duas vagas em playoffs:
  - confronto 1: 3º × 6º; confronto 2: 4º × 5º; vencedores sobem;
  - ida 21/11/2026, volta 28/11/2026; 3º e 4º decidem em casa;
  - sem final entre os vencedores;
  - desempate: pontos nos dois jogos, depois saldo de gols, depois a melhor
    colocação na fase de pontos corridos. **Sem prorrogação e sem pênaltis.**

## Série C

Três fases; a pontuação é zerada no começo de cada fase.

1. **Liga nacional**: 20 clubes, turno único, 19 rodadas. 1º ao 8º avançam;
   19º e 20º são rebaixados à Série D.
2. **Dois quadrangulares** (turno e returno, 6 rodadas):
   - Grupo B: 1º, 4º, 5º e 8º da 1ª fase;
   - Grupo C: 2º, 3º, 6º e 7º da 1ª fase;
   - os dois primeiros de cada grupo sobem à Série B de 2027.
3. **Final**: campeões dos grupos B e C, ida e volta; empate nos critérios vai
   para os pênaltis. Os segundos colocados sobem, mas não jogam a final.

O campeão da Série C entra direto na 3ª fase da Copa do Brasil de 2027.

### Mudança de tamanho

| Temporada | Clubes | Rebaixados |
|---|---|---|
| 2026 | 20 | 2 |
| 2027 | 24 | 2 previstos na transição |
| 2028 | 28 | a confirmar (formato inicial previsto: 2 grupos de 14) |

Para 2027 continua a 1ª fase em grupo único. Manter a Série C com 20 clubes em
todas as temporadas deixaria o mod errado a partir de 2027.

## Série D

- 96 clubes, 6 acessos, sem rebaixamento nacional.
- Lista atual em `data/brasil/series_2026.csv` tem 93 clubes: **faltam 3**.
- Formato detalhado das fases: a registrar.

## O que está aplicado (`scripts/aplicar_brasil_2026.py`)

Validado no jogo com `fm_brasil.exe` (New Game com o Brasil).

| Regra | Situação |
|---|---|
| Nomes Série A, B, C e D | ✅ `.lnc` (`COMP_NAME_CHANGE`, idioma `""`) |
| Clubes de cada série | ✅ banco; lista em `data/brasil/mapa_2026.csv`; clube que não existe no FM06 vira o brasileiro de maior reputação ainda livre |
| Série A: 28/01–02/12, 4 rebaixados | ✅ validado |
| Série B: 21/03–15/11 (pontos corridos), 4 caem | 🟡 fim com folga; playoff sorteado em 20/11, jogos a partir de 22/11 |
| Série B: 1º e 2º sobem; playoffs 3×6 e 4×5, empate passa a melhor campanha | ✅ playoff criado e jogado (teste 5); falta confirmar o desempate na tela |
| Série C: 20 clubes, 4 sobem, 2 caem | ✅ validado (Taça de Prata) |
| Virada de temporada (2006 → 2007) | ✅ as quatro séries recomeçam em 2007 |
| Acesso e rebaixamento na virada | 🟡 teste 7: A↔B e C↔D ✅ (C com 24 em 2007); B↔C não andou porque os grupos da C marcavam "Q" e não "P". Corrigido, a testar |
| Série C 1ª fase: 05/04–23/08, turno único, 8 avançam, 2 caem | ✅ |
| Série C 2ª fase: 2 grupos de 4, ida e volta, 06/09–01/11 (CBF: até 25/10), 2 primeiros de cada grupo sobem | ✅ criada (teste 5); grupos sorteados pelo jogo (ainda não 1-4-5-8 / 2-3-6-7) |
| Série C: final entre os campeões dos grupos | ❌ ainda não; o título fica sem final |
| Série C: 24 clubes em 2027, 28 em 2028 | 🟡 24 em 2007 ✅; 28 a testar: cresce 4 por temporada até 28 (sobem 6 da D, caem 2); com 28 caem 6. A D completa as vagas com clubes de baixo e fica em 96 |
| Série D: 96 clubes, 05/04–28/10 (CBF: até 13/09) | 🟡 as 3 fases são criadas, mas a 10ª rodada dos grupos caiu em 20/09, depois do mata-mata: calendário a ajustar |
| Série D: 6 acessos | 🟡 a testar: mata-mata de 32 e de 16; os 8 restantes jogam fase final em turno único e os 6 primeiros sobem |
| Vagas na Libertadores e Sul-Americana | ❌ não mapeado |
| Copa do Brasil e Supercopa | ❌ a Copa do Brasil (`0x00BB9550`) ainda puxa clubes só das antigas A, B e C |

## Lição dos testes: datas e estaduais

No FM06 os estaduais vão até abril ou maio. Começar B, C e D em março e abril
põe rodadas em cima dos estaduais, e o jogo empurra jogos para depois da data
de fim da fase (B: fim marcado em 8/11, últimos jogos em 11 e 12/11). Se a
fase não terminou na data de fim, ninguém passa para a fase seguinte, a
competição nunca termina e a temporada do Brasil não vira (em fevereiro de
2007 não havia calendário, acesso nem estaduais). Regra: data de fim com
folga e pelo menos uma semana até a fase seguinte. Por isso C e D terminam
algumas semanas depois das datas da CBF.

## Lição dos testes: a fase seguinte precisa ser criada (método 72)

Mesmo com as datas certas, a fase 2 não existia: no FM06 cada liga tem um
método que, quando uma fase termina, cria a seguinte. A Série B e a nova C
usavam o padrão, que não faz nada. Ver `docs/reversing/playoffs.md`.
