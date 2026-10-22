# Testes pendentes no jogo

O que já está no repositório e ainda não foi conferido dentro do FM06. Quando testar,
mande o print e a saída do script; a linha sai desta lista.

## Ordem completa (instalação do zero)

Com o jogo fechado, na pasta do repositório (`C:\Users\Pichau\Desktop\fm06-brasil-2026`):

1. `python scripts\aplicar_brasil_2026.py --apply`: séries, banco, telas, rivais e o
   `fm_brasil.exe`.
2. New Game com o `fm_brasil.exe`; na tela principal:
   `python scripts\live_player_editor.py --squads-all data\brasil\clubes\identidade_fm06.csv`.
   Feche o jogo.
3. `python scripts\reforcar_elencos.py --apply`; depois New Game de novo e o passo 2 de
   novo.
4. `python scripts\montar_elencos.py`
5. `python scripts\aplicar_comissao.py --apply`
6. `python scripts\aplicar_arbitros.py --apply`
7. `python scripts\aplicar_historico.py --apply`
8. Copie `workspace\mods\brasil_2026_jogadores.lnc` para `data\db\lnc\all` do jogo.
9. New Game; na tela principal:
   `python scripts\live_player_editor.py workspace\mods\brasil_2026_jogadores.json --apply`.
   Salve o jogo.

Se você já fez tudo antes e só quer as novidades (rivais, árbitros, técnico da Seleção,
histórico): passos 1, 5, 6, 7 e 9. O passo 1 não mexe no `people_db` nem nos elencos
montados, e o passo 5 pode ser rodado de novo sobre o que já gravou.

## O que conferir

| # | O quê | Onde olhar | Esperado | Script |
|---|---|---|---|---|
| 1 | Histórico de carreira | aba Histórico do jogador | Paquetá: Flamengo 2016–2018, Milan 2019, Lyon 2020–2021, West Ham 2022–2025; Arrascaeta: Defensor 2012–2014, Cruzeiro 2015–2018, Flamengo 2019–2024; um jogador fora da planilha e o técnico do Flamengo: só a temporada atual | `aplicar_historico.py` |
| 2 | Rivais | tela de informações do clube (se mostrar rivais) e notícias depois de um clássico ("diretoria feliz com a vitória no clássico") | Flamengo: Vasco, Fluminense e Botafogo; Novorizontino sem Athletico e Coritiba | `aplicar_brasil_2026.py` |
| 3 | Árbitros de 2026 | tela da partida / relatório ("Árbitro: ...") nos jogos da Série A | Raphael Claus, Wilton Pereira Sampaio, Anderson Daronco... nos jogos grandes | `aplicar_arbitros.py` |
| 4 | Técnico da Seleção | tela da seleção brasileira (Brasil > Seleção) | Carlo Ancelotti, italiano, nascido em 10/6/1959 (66 anos no começo do jogo) | `aplicar_comissao.py` |
| 5 | Nomes dos regens | chegada dos juniores (base) | nomes de hoje (Enzo, Davi, Endrick...) nos brasileiros, argentinos etc. | `aplicar_brasil_2026.py` |
| 6 | Nacionalidade pelo código | saída do injetor (`... nações na memória; nacionalidade pelo código`) e um estrangeiro (Jhon Arias, Palmeiras) | Colômbia; se der certo, eu tiro os 28 doadores de nacionalidade | `live_player_editor.py` |

Se algo der errado:

- histórico: `python scripts\aplicar_historico.py --restore`;
- tudo: `python scripts\aplicar_brasil_2026.py --restore` (banco, histórico, telas,
  `people_db` e os `.lnc` do mod).
