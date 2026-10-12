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

## O que isso exige do FM06 (avaliação inicial)

| Regra | Situação |
|---|---|
| Série A: datas, 4 rebaixados | ✅ patch validado (`serie_a_datas_2026`, `serie_a_rebaixa_4`) |
| Série B: 4 rebaixados | 🟡 patch pronto (`serie_b_rebaixa_4`), falta validar |
| Série B: 2 acessos diretos + playoffs 3×6 e 4×5 sem pênaltis | ❌ exige uma fase de playoff; outras ligas do FM06 têm playoffs para servir de modelo |
| Série C: 20 clubes, 3 fases, 4 acessos, 2 rebaixados | ❌ nova competição (code cave), com fases de liga, quadrangulares e final |
| Série C: 24 clubes em 2027, 28 em 2028 | ❌ o tamanho teria de depender do ano; investigar se o código das fases recebe o ano |
| Série D: 96 clubes, 6 acessos | ❌ reaproveitar a competição de 128 clubes da Série C antiga, redimensionada |
| Vagas na Libertadores e Sul-Americana | ❌ não mapeado |
| Copa do Brasil e Supercopa | ❌ não mapeado |
