# Histórico de campeões

`scripts/aplicar_brasil_2026.py --apply` reescreve, no `server_db.dat`, o histórico
de campeão e vice de:

| Competição | Anos |
|---|---|
| Série A (lista unificada da CBF: Copa dos Campeões 1937, Taça Brasil, Robertão, Brasileirão) | 1937, 1959–2025 |
| Série B | 1971–2025 (sem 1973–79, 1986, 1987, 1993, 2000) |
| Série C (nova) | 1981, 1988, 1990, 1992, 1994–2025 (sem 2000) |
| Série D | 2009–2025 |
| Copa do Brasil | 1989–2025 |
| Libertadores | 1960–2025 |
| Sul-Americana | 2002–2024 (a de 2025 o próprio jogo simula antes do 1º dia) |
| 27 estaduais | do primeiro ano até 2025 |

Fonte: `data/brasil/historico/campeoes.csv`, gerado por
`python scripts/coletar_historico.py` (tabelas de campeões da Wikipédia em
inglês; a Copa do Brasil está no próprio script).

## Como fica no banco

- O jogo mostra os anos com +20 (motor em 2005, tela em 2025): o campeão real do
  ano A é gravado como A − 20.
- Os anos que o banco do FM06 já tinha (até 2005) mantêm o campeão e o vice do
  próprio banco e só mudam de ano.
- A antiga Série C (hoje a Série D) passa o histórico para a nova Série C; os
  registros da Taça de Prata (Robertão 1967–70) passam para a Série A.
- Os anos que faltavam usam 617 registros órfãos do banco (de competições que não
  existem mais) e 117 registros novos no fim da lista
  (`src/fm06patch/campeoes.py`).
- Clube que não está no jogo, ou cujo time de 2005 virou substituto de outro
  clube de 2026 (São Caetano, Santo André, Paulista, Rio Negro-AM…), fica em
  branco: no jogo ele teria o nome do clube novo. A lista está em
  `data/brasil/historico/sem_clube_no_jogo.txt`.
- As outras competições do mundo não mudam (continuam com os anos do FM06 + 20).

## Conferir no jogo

New Game e abra, por exemplo:

- Série A → Histórico: 2025 Flamengo (vice Palmeiras), 2024 Botafogo, 1959 Bahia;
- Série D → Histórico: 2025 Barra, 2009 São Raimundo-PA;
- Libertadores → Histórico: 2025 Flamengo, 2024 Botafogo, 2016 Atlético Nacional;
- Campeonato Paulista → Histórico: 2025 Corinthians, 2024 Palmeiras;
- a ficha de títulos de um clube (Palmeiras, Flamengo).

Se o New Game travar ou o histórico vier estranho, rode
`python scripts\aplicar_brasil_2026.py --apply --sem-historico` (volta ao
comportamento anterior: só os campeões de 2025) e me mande o que apareceu.
