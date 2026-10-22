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

Nome: apelido do Sofascore quando há (Pedro, Danilo); se não, o nome conhecido do
endereço do jogador (fabio-ferreira -> Fábio Ferreira); se não, primeiro nome +
último sobrenome, como o FM mostra (Renan Peixoto Nepomuceno -> Renan Nepomuceno;
brasileiro sem "de": Enzo Souza; com sufixo: Silva Filho).

Contrato (gravado pelo injetor no contrato do clube, `reverse/fmm/FMM_SCHEMA.md`):
início (+24) e fim (+32) com o year_shift, número da camisa (+49, byte) e, quando
`config/local.json` tiver `"wage_factor"`, o salário (+16, valor×10+2). O fator é a
unidade do jogo por R$ mensal: `live_player_editor.py --show <UID>` mostra o
salário bruto de um jogador, para comparar com o que a ficha mostra. Medido no Pulgar:
bruto 639 = R$ 13.000 por mês na ficha, ou seja, libras por semana × 4 × 5,08; com o
salário gravado como valor × 10 + 2, `"wage_factor": 0.00492`.

Perfil (`data/modelos/jogadores_perfil.xlsx`, ligado pelo `montar_elencos.py`):
personalidade (PData +8..+15), os ocultos consistência, jogos importantes,
propensão a lesão, versatilidade e jogo sujo (atributos absolutos, 5 × nota + 2) e as
jogadas preferidas: as da planilha entram e as outras 47 saem. Jogos e gols pela
seleção (`jogos_selecao`, `gols_selecao` da planilha de jogadores) vão em Player +72
e +74 (u8).

## No jogo

Cada jogador de 2026 ocupa um jogador de 2005 do mesmo clube (o jogo não cria
jogador adulto). Primeiro a equipe principal, depois a base, até acabarem os
jogadores de 2005 do clube.

1. New Game com o `fm_brasil.exe`. Na tela principal:
   `python scripts\live_player_editor.py --squads-all data\brasil\clubes\identidade_fm06.csv`
   (grava `workspace\elencos_2005.csv`).
2. `python scripts\montar_elencos.py` (grava em `workspace\mods\`). Depois dele (e do
   `aplicar_comissao.py`), com o jogo fechado: `python scripts\aplicar_historico.py --apply`
   (histórico de carreira, ver abaixo).
3. Copie `workspace\mods\brasil_2026_jogadores.lnc` para
   `data\db\lnc\all` do jogo e comece **outro** New Game (os nomes entram).
4. `python scripts\live_player_editor.py workspace\mods\brasil_2026_jogadores.json`
   (confere) e de novo com `--apply`. Salve o jogo.

`workspace\mods\brasil_2026_jogadores_sem_vaga.csv` lista quem ficou de fora
por falta de jogador de 2005 no clube.

### Histórico de carreira (aba Histórico)

`scripts\aplicar_historico.py --apply` grava `data\db\pl_hist_index.dat`,
`pl_hist_id.dat` e `pl_hist_dt.dat` (o jogo lê no New Game), sempre a partir do original
(cópia em `workspace\baseline\pl_hist_*.original.dat`; `--restore` volta):

- os jogadores de `data\modelos\historico_carreira.xlsx` (hoje os 100 de maior CA) ganham
  a carreira de verdade. A planilha traz o total de cada passagem; jogos e gols são
  repartidos por igual entre as temporadas dela, então o total do clube fica certo e o
  de cada temporada é aproximado. O ano em que começa a passagem seguinte é dela
  (Paquetá: Flamengo 2016–2018, Milan 2019, Lyon 2020–2021, West Ham 2022–2025). No ano
  de um empréstimo só aparece o clube do empréstimo, como no banco da SI. Passagem em
  aberto ("2019–") vai até 2026; a temporada de 2025 no clube de 2026 e a de 2026 ficam
  de fora, porque o jogo começa nelas e põe a linha dele;
- os outros jogadores de 2026 e a comissão de 2026 perdem a carreira do jogador de 2005
  que ocupam: aparece só a temporada atual;
- os jogadores de 2005 que sobram (nome de hoje) ficam com a carreira que tinham.

Clubes: os brasileiros pela `identidade_fm06.csv` (o clube de 2026 no jogo), os outros pelo
nome no `lang_db` (o mais citado no histórico quando há mais de um: "Barcelona" é o
espanhol); os casos difíceis estão em `ALIASES` (`src/fm06patch/historico_jogadores.py`:
"Porto" é o de Portugal, "Racing" o da Argentina). O script mostra os achados por
aproximação (`[CONFIRA]`) e os clubes que não existem no banco de 2005 (a passagem fica
de fora: Independiente del Valle, MLS de hoje, Patriotas...). A lista do que entrou, com
as temporadas gravadas, fica em `workspace\mods\historico_2026.csv`.

### Reforço: clubes com poucos jogadores de 2005

`scripts\reforcar_elencos.py --apply` (depois do passo 1) muda no
`people_db.dat` o clube do contrato de jogadores de clubes que não usamos
(brasileiros fora de 2026, depois até 2 por clube estrangeiro), até cada clube
ter vaga para o elenco de 2026 (até 45). Ao contrário, os jogadores de 2005 do
banco que passam do tamanho do elenco de 2026 (Internacional: 93 para 65) saem para
clubes brasileiros fora de 2026, para não ficarem no elenco com o nome de 2005. Depois: New Game e passos 1 a 4 de
novo. O jogo põe a pessoa no time do campo "time" do registro (o mesmo do staff,
`docs/reversing/people-db.md`), que tem de bater com o clube do contrato: o reforço
muda os dois (mudar só o contrato tirava o jogador do clube antigo sem pô-lo no novo).
O campo "time" é achado procurando os nomes para trás a partir do contrato; a busca
para no fim do registro anterior (`comissao._record_start`). Sem esse limite, em 18
jogadores ela caía no registro da pessoa anterior e gravava o time nela: essa pessoa ia
para um time de 2026 com o contrato do clube antigo, que não carrega, e o jogo travava
com o clube do contrato nulo (no New Game, 0x00A2B2F3, calculando prêmios do contrato;
em junho, 0x0078B854, numa proposta de troca). Quem não tem o registro achado não muda
(o reforço avisa quantos).
`src/fm06patch/people_contracts.py`: o contrato fica no fim do registro
da pessoa (00, u32 índice do clube, u32, u16 dia e u16 ano do fim, 02 00 00
00); o clube é citado pelo índice, e cada registro de clube do server_db
termina com o próprio (índice, UID).

Outro `.lnc` com `CHANGE_PLAYER_NAME` na pasta do jogo (como o teste antigo
`flamengo_2026.lnc`) dá nome aos mesmos jogadores numa ordem diferente e
embaralha os nomes; o `montar_elencos.py` avisa.

Nacionalidade: vai pelo código da nação (abaixo). Até 22/10/2026 havia também os
"doadores": um jogador de 2005 de cada nação, levado pelo `reforcar_elencos.py` para um
clube de 2026 e mantido no elenco com o nome de 2005, para o injetor copiar a
nacionalidade dele. Com o código conferido no jogo (400 de 400 no injetor; Jhon Arias
colombiano), os doadores saíram: ninguém mais é levado para isso, e quem era doador num
clube de 2026 vira hospedeiro comum. O código da nação vem do `people_db`: depois do nome
completo vêm o ano de nascimento e o código (0xBB Argentina, 0xBC Bolívia, 0xBD Brasil,
0xBE Chile, 0xBF Colômbia, 0xC0 Equador, 0xC1 Paraguai, 0xC2 Peru, 0xC3 Uruguai, 0xC4
Venezuela, 0xA2 Portugal, 0xAA Espanha…).

Contrato sem data de fim: 2.353 jogadores brasileiros do banco (quase todos das séries de
baixo) têm o fim em 1900 e salário 0; no jogo aparecem com contrato normal. O
`people_contracts.contracts()` conta esses também; antes ficavam de fora, e os clubes
grandes ficavam com dezenas de jogadores de 2005 além do elenco de 2026 (Grêmio 110 no
jogo para 65 na planilha). Agora o reforço tira 323 sobras (antes 98).

Nacionalidade pelo código: o `montar_elencos.py` grava `nationality_code` (o código do
people_db, `people_contracts.NATION_CODES`) e o injetor acha o objeto Nation na memória
pela assinatura (`live_player.NATION_SIGNATURE`, número da nação em +24). Antes de usar,
confere com os jogadores que vai editar: o ponteiro de nacionalidade deles tem de cair
num objeto Nation (`nation_pointers`); se não conferir, a nacionalidade não muda. Os códigos
novos (Itália 0x96, Coreia do Sul 0x50, Arábia Saudita 0x4E...) foram conferidos pelos
sobrenomes de cada nação na tabela de nomes do server_db.
