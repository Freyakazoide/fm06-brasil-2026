# Testes pendentes no jogo

O que já está no repositório e ainda não foi conferido dentro do FM06. Quando testar,
mande o print e a saída do script; a linha sai desta lista.

## Como rodar tudo

Um comando só, na pasta do repositório (`C:\Users\Pichau\Desktop\fm06-brasil-2026`):

    python scripts\aplicar_tudo.py

Ele roda os scripts na ordem e para quando é hora de abrir ou fechar o jogo (aperte
Enter quando estiver pronto):

1. jogo fechado: `aplicar_brasil_2026.py` e `reforcar_elencos.py`;
2. jogo aberto (New Game, tela principal): conta os jogadores de 2005 de cada clube; depois
   feche o jogo;
3. jogo fechado: `montar_elencos.py`, `aplicar_comissao.py`, `aplicar_arbitros.py`,
   `aplicar_historico.py` e a cópia do `.lnc` dos jogadores;
4. jogo aberto (outro New Game, tela principal): o injetor. Salve o jogo.

- `python scripts\aplicar_tudo.py --rapido`: pula a contagem (etapa 2), para quando os
  elencos não mudaram (só tradução, comissão, árbitros, histórico, rivais...). Refaz o
  reforço e para se o people_db não for o da última contagem completa.
- `python scripts\aplicar_tudo.py --etapa 3`: recomeça da etapa 3 depois de um erro.

## O que conferir

| # | O quê | Onde olhar | Esperado | Script |
|---|---|---|---|---|
| 1 | ~~Histórico de carreira~~ ✅ conferido em 22/10 | aba Histórico do jogador | Paquetá: Flamengo 2016–2018, Milan 2019, Lyon 2020–2021, West Ham 2022–2025; Arrascaeta: Defensor 2012–2014, Cruzeiro 2015–2018, Flamengo 2019–2024; um jogador fora da planilha e o técnico do Flamengo: só a temporada atual | `aplicar_historico.py` |
| 2 | Rivais | tela de informações do clube (se mostrar rivais) e notícias depois de um clássico ("diretoria feliz com a vitória no clássico") | Flamengo: Vasco, Fluminense e Botafogo; Novorizontino sem Athletico e Coritiba | `aplicar_brasil_2026.py` |
| 3 | Árbitros de 2026 | tela da partida / relatório ("Árbitro: ...") nos jogos da Série A | Raphael Claus, Wilton Pereira Sampaio, Anderson Daronco... nos jogos grandes | `aplicar_arbitros.py` |
| 4 | ~~Técnico da Seleção~~ ✅ conferido em 22/10 | tela da seleção brasileira (Brasil > Seleção) | Carlo Ancelotti, italiano, nascido em 10/6/1959 (66 anos no começo do jogo) | `aplicar_comissao.py` |
| 5 | Nomes dos regens | chegada dos juniores (base) | nomes de hoje (Enzo, Davi, Endrick...) nos brasileiros, argentinos etc. | `aplicar_brasil_2026.py` |
| 6 | Sem doadores de nacionalidade | elencos com estrangeiros (Palmeiras, Flamengo) | nenhum jogador de 2005 com nome antigo no elenco; estrangeiros de 2026 com a nação certa | `aplicar_tudo.py` |
| 7 | Joias da base (25 garotos) | chegada dos juniores (o jogo avisa nas notícias do clube); depois procure o nome | Vitor Wachter (Grêmio), Arthur Vale e João Sá (Santos), Breno Sales (Vasco), Leonardo Cerci (Athletico-PR), Miguel Messias e mais 10 no Palmeiras; idade, clube e nacionalidade certos (atributos e posição o jogo sorteia) | `aplicar_brasil_2026.py` (`brasil_2026_regens.edt`) |
| 8 | Carreira de todos os jogadores (transferências) | aba Histórico de jogadores fora dos 100 da planilha | Felipe Anderson (Palmeiras): Santos 2010–2012, Lazio 2013–2017, West Ham 2018–2019, Porto (empréstimo) 2020, Lazio 2021–2023, com valor nas vendas; Yago Pikachu (Remo): Paysandu, Vasco, Fortaleza, Shimizu, Fortaleza; Steven Mendoza (Athletico-PR): Envigado, América de Cali e Cúcuta (empréstimos), Deportivo Cali, Corinthians, Bahia (empréstimo), Amiens, Ceará, Santos, Adana Demirspor, León. Jogos e gols sem dado (me diga como o jogo mostra: "-", 0 ou vazio) | `aplicar_historico.py` (`carreiras_2026.csv`) |
| 9 | CT e base dos 40 clubes das Séries A e B | tela de informações do clube (frase das instalações) | Palmeiras, Flamengo e Cuiabá com a frase mais alta ("Top facilities plus youth academy", ou a tradução); São Bernardo "Good facilities"; Remo "Average facilities"; antes, o Cuiabá aparecia com instalações ruins | `aplicar_brasil_2026.py` (aba Estrutura) |
| 10 | Técnicos das seleções sul-americanas | tela de cada seleção (Argentina, Uruguai, Venezuela...) | Scaloni (ARG), Óscar Villegas (BOL), Néstor Lorenzo (COL), Gallardo (ECU), Alfaro (PAR), Mano Menezes (PER), Forlán (URU), Vizcarrondo (VEN) | `aplicar_comissao.py` |
| 11 | Sem gente repetida | procurar pelo nome (busca de pessoas): Carlo Ancelotti, Diego Forlán, Tite, Abel Ferreira | só uma pessoa com cada nome (a de 2026). O técnico do Milan de 2005 e o Forlán jogador do Villarreal ganham nomes de hoje do país deles | `aplicar_comissao.py` |
| 12 | Elencos com a lista do time no server_db (correção de 24/10; rodada completa, sem `--rapido`) | elencos do Red Bull Bragantino, Cuiabá, Athletico-PR, Trem; o Palmeiras; a comissão de quem recebeu gente de fora (Ceará, Fortaleza, Náutico) | Bragantino e Cuiabá com os jogadores de 2026 e sem juniores inventados ("Alamosi"); Warley fora do Palmeiras; Zé Eduardo no clube dele; o clube da ficha igual ao da lista; os auxiliares, preparadores e fisioterapeutas trazidos de fora aparecendo no staff do clube. Na saída: "N jogadores mudados de elenco no server_db.dat" e "N da comissão mudados de clube" | `aplicar_tudo.py` |

Antes de rodar, `python scripts\validar_entregas.py` confere as planilhas.

Se algo der errado:

- histórico: `python scripts\aplicar_historico.py --restore`;
- tudo: `python scripts\aplicar_brasil_2026.py --restore` (banco, histórico, telas,
  `people_db` e os `.lnc` do mod).
