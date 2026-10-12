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

| Regra | Situação |
|---|---|
| Nomes Série A, B, C e D | 🟡 `.lnc` (`COMP_NAME_CHANGE`, idioma `""`), a testar |
| Clubes de cada série | 🟡 banco; lista em `data/brasil/mapa_2026.csv`; clube que não existe no FM06 vira o brasileiro de maior reputação ainda livre |
| Série A: 28/01–02/12, 4 rebaixados | ✅ validado |
| Série B: 21/03–28/11, 4 sobem, 4 caem | 🟡 datas e rebaixamento a testar |
| Série B: playoffs 3×6 e 4×5 | ❌ por enquanto sobem 1º a 4º direto |
| Série C: 20 clubes, 4 sobem, 2 caem | ✅ validado (Taça de Prata) |
| Série C: 05/04–25/10, turno único | 🟡 a testar |
| Série C: quadrangulares e final | ❌ por enquanto sobem 1º a 4º direto da fase de liga |
| Série C: 24 clubes em 2027, 28 em 2028 | ❌ |
| Série D: 96 clubes, 05/04–13/09 | 🟡 16 grupos de 6, 2 avançam, mata-mata de 32, quadrangular final |
| Série D: 6 acessos | ❌ por enquanto 4 (os do quadrangular final); 6 exige refazer o mata-mata |
| Vagas na Libertadores e Sul-Americana | ❌ não mapeado |
| Copa do Brasil e Supercopa | ❌ a Copa do Brasil (`0x00BB9550`) ainda puxa clubes só das antigas A, B e C |
