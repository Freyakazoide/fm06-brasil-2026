# Jogadores de 2026 (Séries A, B, C e D)

## Dados

`scripts/coletar_sofascore.py` baixa do Sofascore (API pública) os elencos de
2026 dos 156 clubes das quatro séries e o sub-20 de cada um. Clube com menos de
20 jogadores listados ganha quem jogou por ele em 2026 (escalações). O cache
fica em `workspace/sofascore` (um JSON por pedido; rodar de novo só baixa o
que falta).

`scripts/montar_jogadores.py` grava `data/brasil/jogadores/jogadores_2026.xlsx`
(colunas do modelo `jogadores_2026_modelo.xlsx`):

| Dado | Origem |
|---|---|
| nome, número, posições, nascimento, altura, pé, nacionalidade | Sofascore |
| fim do contrato, valor de mercado | Sofascore |
| início do contrato, empréstimo (de quem) | última transferência para o clube (tipo 1 = empréstimo) |
| jogos e gols pela seleção | Sofascore (só seleção principal) |
| peso | estimado pela altura (IMC 23,2; goleiro 24) |
| salário | estimado: ~10% do valor de mercado por ano, piso por série |
| CA | `104 + 22 × log10(valor / 100 mil)` − desconto da série (A 0, B 3, C 8, D 14), − 2,5 por ano abaixo de 23, + 2,5 por ano de 31 a 35 e − 3 por ano depois dos 35, + até 8 pelos jogos na seleção (1 a cada 8). Mais de 47 anos: fora (erro de cadastro). Sem valor: A 118, B 100, C 88, D 76 (sub-20: A 82, B 74, C 66, D 58, + 4 por ano acima de 17) |
| PA | CA + crescimento pela idade (40 aos 15 … 2 aos 26), ± 8 fixo por jogador até 22 anos, + até 12 para jovem de valor alto |
| destaques | visão geral do Sofascore (ataque, técnica, tática, defesa, criatividade; goleiro: defesas, antecipação, distribuição, jogo aéreo) deslocando os atributos ligados a ela |
| situação | os 11 de maior CA titulares, os 9 seguintes rotação; sub-20 = "Base (sub-20)" (até 30 por clube, maior PA) |

O que foi estimado por falta de dado está na coluna `obs`.

## No jogo

Cada jogador de 2026 ocupa um jogador de 2005 do mesmo clube (o jogo não cria
jogador adulto). Primeiro a equipe principal, depois a base, até acabarem os
jogadores de 2005 do clube.

1. New Game com o `fm_brasil.exe`. Na tela principal:
   `python scripts\live_player_editor.py --squads-all data\brasil\clubes\identidade_fm06.csv`
   (grava `workspace\elencos_2005.csv`).
2. `python scripts\montar_elencos.py` (grava em `workspace\mods\`).
3. Copie `workspace\mods\brasil_2026_jogadores.lnc` para
   `data\db\lnc\all` do jogo e comece **outro** New Game (os nomes entram).
4. `python scripts\live_player_editor.py workspace\mods\brasil_2026_jogadores.json`
   (confere) e de novo com `--apply`. Salve o jogo.

`workspace\mods\brasil_2026_jogadores_sem_vaga.csv` lista quem ficou de fora
por falta de jogador de 2005 no clube.

### Reforço: clubes com poucos jogadores de 2005

`scripts\reforcar_elencos.py --apply` (depois do passo 1) muda no
`people_db.dat` o clube do contrato de jogadores de clubes que não usamos
(brasileiros fora de 2026, depois até 2 por clube estrangeiro), até cada clube
ter vaga para o elenco de 2026 (até 45). Depois: New Game e passos 1 a 4 de
novo. `src/fm06patch/people_contracts.py`: o contrato fica no fim do registro
da pessoa (00, u32 índice do clube, u32, u16 dia e u16 ano do fim, 02 00 00
00); o clube é citado pelo índice, e cada registro de clube do server_db
termina com o próprio (índice, UID).

Outro `.lnc` com `CHANGE_PLAYER_NAME` na pasta do jogo (como o teste antigo
`flamengo_2026.lnc`) dá nome aos mesmos jogadores numa ordem diferente e
embaralha os nomes; o `montar_elencos.py` avisa.

Nacionalidade: `nationality_like` copia a de um jogador de 2005
(`squad_builder.NATIONALITY_DONORS`). Os doadores novos vieram do `people_db`:
depois do nome completo vêm o ano de nascimento e o código da nação (0xBB
Argentina, 0xBC Bolívia, 0xBD Brasil, 0xBE Chile, 0xBF Colômbia, 0xC0 Equador,
0xC1 Paraguai, 0xC2 Peru, 0xC3 Uruguai, 0xC4 Venezuela, 0xA2 Portugal, 0xAA
Espanha…); o registro termina com (índice, UID).
