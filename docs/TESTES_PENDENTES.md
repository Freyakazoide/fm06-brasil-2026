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

- `python scripts\aplicar_tudo.py --rapido`: pula o reforço e a contagem (etapa 2), para
  quando os elencos não mudaram (só tradução, comissão, árbitros, histórico, rivais...).
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

Se algo der errado:

- histórico: `python scripts\aplicar_historico.py --restore`;
- tudo: `python scripts\aplicar_brasil_2026.py --restore` (banco, histórico, telas,
  `people_db` e os `.lnc` do mod).
